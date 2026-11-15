"""
End-to-end CPU training and evaluation for VeriSight AI Audio Spoof Classifier.
Uses ASVspoof 2019 LA dataset with class-balanced subsets for fast CPU training.
Generates genuine training metrics: accuracy, precision, recall, F1, ROC-AUC, EER, and confusion matrix.
Saves model checkpoints, evaluation reports, and updates the model registry.
"""

import argparse
import json
import logging
from pathlib import Path
import random
import time

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
    roc_curve,
)
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .audio_dataset import (
    SR,
    DURATION_SEC,
    N_FFT,
    HOP,
    N_MELS,
    TARGET_SAMPLES,
    audio_to_logmel,
    balanced_subset,
    build_protocol_manifest,
    CachedAudioDataset,
)
from .model import AudioSpoofCNN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_audio")

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


def calculate_eer(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Computes Equal Error Rate (EER) where False Acceptance Rate equals False Rejection Rate."""
    fpr, tpr, _ = roc_curve(y_true, scores)
    fnr = 1.0 - tpr
    idx = int(np.nanargmin(np.abs(fnr - fpr)))
    return float((fpr[idx] + fnr[idx]) / 2.0)


def build_or_load_cache(df: pd.DataFrame, prefix: str, cache_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Extracts and caches (N, 1, 64, 201) Log-Mel spectrograms for fast iteration."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    x_path = cache_dir / f"{prefix}_X.npy"
    y_path = cache_dir / f"{prefix}_y.npy"

    if x_path.exists() and y_path.exists():
        try:
            X = np.load(x_path, mmap_mode="r")
            y = np.load(y_path)
            if len(X) == len(df) and len(y) == len(df):
                logger.info(f"Reusing feature cache for {prefix}: {X.shape}")
                return X, y
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}. Rebuilding...")

    logger.info(f"Extracting features for {prefix} ({len(df)} files)...")
    sample_feat = audio_to_logmel(df.iloc[0]["audio_path"])
    X_mm = np.lib.format.open_memmap(
        x_path,
        mode="w+",
        dtype=np.float32,
        shape=(len(df), 1, sample_feat.shape[0], sample_feat.shape[1])
    )
    y = df["label_id"].to_numpy(dtype=np.int64)

    t0 = time.time()
    for i, row in enumerate(df.itertuples()):
        feat = sample_feat if i == 0 else audio_to_logmel(row.audio_path)
        X_mm[i, 0] = feat
        if (i + 1) % 100 == 0 or (i + 1) == len(df):
            logger.info(f"{prefix} feature progress: {i + 1}/{len(df)} ({round(time.time() - t0, 1)}s)")

    X_mm.flush()
    np.save(y_path, y)
    logger.info(f"Finished {prefix} feature cache: shape {X_mm.shape}")
    return np.load(x_path, mmap_mode="r"), y


def run_epoch(model: nn.Module, loader: DataLoader, criterion: nn.Module, optimizer=None):
    """Runs a single train or validation pass."""
    is_training = optimizer is not None
    model.train(is_training)
    total_loss = 0.0
    all_y = []
    all_prob = []

    for xb, yb in loader:
        if is_training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(is_training):
            logits = model(xb)
            loss = criterion(logits, yb)
            if is_training:
                loss.backward()
                optimizer.step()

        total_loss += loss.item() * len(yb)
        probs = torch.softmax(logits.detach(), dim=1)[:, 1]
        all_prob.extend(probs.cpu().numpy().tolist())
        all_y.extend(yb.cpu().numpy().tolist())

    avg_loss = total_loss / max(1, len(loader.dataset))
    return avg_loss, np.asarray(all_y), np.asarray(all_prob)


def train_and_evaluate(
    data_root: Path,
    output_dir: Path,
    registry_path: Path,
    train_per_class: int = 500,
    dev_per_class: int = 200,
    epochs: int = 6,
    batch_size: int = 32,
    lr: float = 1e-3,
    patience: int = 3
):
    device = torch.device("cpu")
    torch.set_num_threads(2)

    logger.info(f"Using CPU device with {torch.get_num_threads()} threads")
    logger.info(f"Dataset root: {data_root}")

    train_proto = data_root / "ASVspoof2019_LA_cm_protocols" / "ASVspoof2019.LA.cm.train.trn.txt"
    dev_proto = data_root / "ASVspoof2019_LA_cm_protocols" / "ASVspoof2019.LA.cm.dev.trl.txt"
    train_audio = data_root / "ASVspoof2019_LA_train" / "flac"
    dev_audio = data_root / "ASVspoof2019_LA_dev" / "flac"

    logger.info("Building manifests from ASVspoof 2019 protocols...")
    train_full = build_protocol_manifest("train", train_proto, train_audio)
    dev_full = build_protocol_manifest("dev", dev_proto, dev_audio)
    logger.info(f"Available train rows: {len(train_full)}, dev rows: {len(dev_full)}")

    train_subset = balanced_subset(train_full, train_per_class, seed=SEED)
    dev_subset = balanced_subset(dev_full, dev_per_class, seed=SEED + 1)
    logger.info(f"Balanced train subset: {len(train_subset)} ({train_subset['label'].value_counts().to_dict()})")
    logger.info(f"Balanced dev subset: {len(dev_subset)} ({dev_subset['label'].value_counts().to_dict()})")

    # Cache features
    cache_dir = output_dir / "cache"
    X_train, y_train = build_or_load_cache(train_subset, "train", cache_dir)
    X_dev, y_dev = build_or_load_cache(dev_subset, "dev", cache_dir)

    train_loader = DataLoader(
        CachedAudioDataset(X_train, y_train),
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )
    dev_loader = DataLoader(
        CachedAudioDataset(X_dev, y_dev),
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=0
    )

    model = AudioSpoofCNN().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    best_auc = -1.0
    best_state = None
    history = []
    wait = 0

    logger.info("Starting CPU training epochs...")
    for epoch in range(1, epochs + 1):
        t0 = time.time()
        train_loss, _, _ = run_epoch(model, train_loader, criterion, optimizer)
        dev_loss, y_true, y_prob = run_epoch(model, dev_loader, criterion)
        elapsed = time.time() - t0

        try:
            dev_auc = float(roc_auc_score(y_true, y_prob))
        except ValueError:
            dev_auc = float("nan")

        row = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "dev_loss": round(dev_loss, 4),
            "dev_auc": round(dev_auc, 4),
            "elapsed_sec": round(elapsed, 2)
        }
        history.append(row)
        logger.info(f"Epoch {epoch}/{epochs} -> train_loss: {row['train_loss']}, dev_loss: {row['dev_loss']}, dev_auc: {row['dev_auc']} ({row['elapsed_sec']}s)")

        if np.isfinite(dev_auc) and dev_auc > best_auc:
            best_auc = dev_auc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                logger.info(f"Early stopping triggered at epoch {epoch}")
                break

    if best_state is None:
        best_state = model.state_dict()

    model.load_state_dict(best_state)

    # Final evaluation on dev
    dev_loss, y_true, y_prob = run_epoch(model, dev_loader, criterion)
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    best_idx = int(np.argmax(tpr - fpr))
    best_threshold = float(thresholds[best_idx])
    y_pred = (y_prob >= best_threshold).astype(int)

    eer_val = calculate_eer(y_true, y_prob)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    report = classification_report(
        y_true,
        y_pred,
        target_names=["bonafide", "spoof"],
        output_dict=True,
        zero_division=0
    )

    metrics = {
        "threshold_selected_on_dev": round(best_threshold, 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "precision_spoof": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall_spoof": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_spoof": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "eer_approx": round(eer_val, 4),
        "confusion_matrix": {
            "bonafide": {"predicted_bonafide": cm[0][0], "predicted_spoof": cm[0][1]},
            "spoof": {"predicted_bonafide": cm[1][0], "predicted_spoof": cm[1][1]}
        },
        "raw_confusion_matrix": cm,
        "dev_loss": round(dev_loss, 4),
        "dev_samples": int(len(y_true)),
        "train_samples": int(len(train_subset))
    }

    logger.info("Evaluation metrics successfully computed:")
    logger.info(json.dumps(metrics, indent=2))

    # Save artifacts
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "verisight_audio_cnn_cpu.pth"
    metadata_path = output_dir / "verisight_audio_cnn_metadata.json"
    metrics_path = output_dir / "audio_dev_metrics.json"
    history_path = output_dir / "audio_training_history.csv"

    torch.save({
        "model_state_dict": best_state,
        "threshold": best_threshold,
        "class_to_id": {"bonafide": 0, "spoof": 1},
        "sample_rate": SR,
        "duration_sec": DURATION_SEC,
        "n_fft": N_FFT,
        "hop_length": HOP,
        "n_mels": N_MELS,
        "architecture": "AudioSpoofCNN",
        "metrics": metrics
    }, checkpoint_path)

    metadata = {
        "model_name": "VeriSight AI CPU Audio Spoof CNN",
        "architecture": "small 2D CNN on normalised log-Mel spectrograms",
        "dataset": "ASVspoof 2019 LA",
        "train_subset_size": int(len(train_subset)),
        "dev_subset_size": int(len(dev_subset)),
        "train_class_counts": train_subset["label"].value_counts().to_dict(),
        "dev_class_counts": dev_subset["label"].value_counts().to_dict(),
        "sample_rate": SR,
        "duration_sec": DURATION_SEC,
        "n_fft": N_FFT,
        "hop_length": HOP,
        "n_mels": N_MELS,
        "threshold_selected_on_dev": best_threshold,
        "metrics": metrics,
        "classification_report": report,
        "limitations": [
            "CPU experiment using balanced subset for fast reproducible execution",
            "DEV metrics are validation results on ASVspoof 2019 LA dev protocol",
            "Audio detector score is a forensic signal, not absolute legal proof"
        ]
    }

    metadata_path.write_text(json.dumps(metadata, indent=2))
    metrics_path.write_text(json.dumps(metrics, indent=2))
    pd.DataFrame(history).to_csv(history_path, index=False)

    # Save manifests
    manifest_dir = output_dir.parent.parent / "data" / "processed" / "audio_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    train_subset.to_csv(manifest_dir / "verisight_audio_train_subset.csv", index=False)
    dev_subset.to_csv(manifest_dir / "verisight_audio_dev_subset.csv", index=False)

    # Update model_registry.json
    if registry_path.exists():
        with registry_path.open("r", encoding="utf-8") as f:
            registry = json.load(f)
        registry["audio"] = {
            "status": "trained",
            "architecture": "AudioSpoofCNN (Log-Mel + 2D CNN)",
            "weights_path": str(checkpoint_path.relative_to(output_dir.parent.parent)).replace("\\", "/"),
            "note": (
                f"Audio deepfake detection model trained on ASVspoof 2019 LA. "
                f"Dev ROC-AUC: {metrics['roc_auc']:.3f}, EER: {metrics['eer_approx']:.3f}, "
                f"Accuracy: {metrics['accuracy']:.3f}."
            ),
            "metrics": metrics
        }
        with registry_path.open("w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        logger.info(f"Updated model registry at {registry_path}")

    logger.info(f"Training completed successfully. Checkpoint: {checkpoint_path}")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train VeriSight AI Audio Spoof CNN on CPU")
    project_root = Path(__file__).resolve().parents[3]
    default_data = Path(r"C:\Users\DELL\Downloads\LA\LA")

    parser.add_argument("--data_root", type=Path, default=default_data)
    parser.add_argument("--output_dir", type=Path, default=project_root / "models" / "audio")
    parser.add_argument("--registry_path", type=Path, default=project_root / "configs" / "model_registry.json")
    parser.add_argument("--train_per_class", type=int, default=500)
    parser.add_argument("--dev_per_class", type=int, default=200)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch_size", type=int, default=32)

    args = parser.parse_args()
    train_and_evaluate(
        data_root=args.data_root,
        output_dir=args.output_dir,
        registry_path=args.registry_path,
        train_per_class=args.train_per_class,
        dev_per_class=args.dev_per_class,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
