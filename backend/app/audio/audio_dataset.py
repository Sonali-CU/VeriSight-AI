"""
Audio dataset preparation, Log-Mel extraction, and protocol parsing for ASVspoof 2019 LA.
Designed for CPU execution with reproducible balanced subsets.
"""

from pathlib import Path
import random
import numpy as np
import pandas as pd
import soundfile as sf
import torch
import torch.nn.functional as F
import torchaudio
from torch.utils.data import Dataset

SR = 16000
DURATION_SEC = 2
TARGET_SAMPLES = SR * DURATION_SEC  # 32000
N_FFT = 512
HOP = 160
N_MELS = 64

_mel_transform = None


def get_mel_transform():
    """Singleton for torchaudio MelSpectrogram transform."""
    global _mel_transform
    if _mel_transform is None:
        _mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=SR,
            n_fft=N_FFT,
            hop_length=HOP,
            n_mels=N_MELS,
            power=2.0
        )
    return _mel_transform


def load_fixed_audio(path: str | Path, target_samples: int = TARGET_SAMPLES) -> torch.Tensor:
    """
    Loads an audio file as mono 16 kHz float32 and ensures fixed length.
    Crops if longer, zero-pads at end if shorter.
    """
    path = str(path)
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    audio = np.nan_to_num(audio, copy=False)
    x = torch.from_numpy(np.asarray(audio, dtype=np.float32))

    if sr != SR:
        x = torchaudio.functional.resample(x, orig_freq=sr, new_freq=SR)

    if x.numel() > target_samples:
        x = x[:target_samples]
    elif x.numel() < target_samples:
        x = F.pad(x, (0, target_samples - x.numel()))

    return x


def audio_to_logmel(path: str | Path) -> np.ndarray:
    """
    Converts audio at path to a normalized Log-Mel spectrogram.
    Shape: (64, 201), dtype: float32.
    """
    x = load_fixed_audio(path)
    transform = get_mel_transform()
    with torch.no_grad():
        mel = transform(x.unsqueeze(0))
        logmel = torch.log(mel + 1e-6)
        logmel = (logmel - logmel.mean()) / (logmel.std() + 1e-5)
    return logmel.squeeze(0).numpy().astype(np.float32)


def build_protocol_manifest(split: str, protocol_path: Path, audio_dir: Path) -> pd.DataFrame:
    """
    Parses an ASVspoof 2019 LA protocol file and verifies audio file existence.
    """
    if not protocol_path.is_file():
        raise FileNotFoundError(f"Missing protocol file: {protocol_path}")
    if not audio_dir.is_dir():
        raise FileNotFoundError(f"Missing audio directory: {audio_dir}")

    proto = pd.read_csv(
        protocol_path,
        sep=r"\s+",
        header=None,
        names=["speaker_id", "filename", "system_id", "attack_id", "label"]
    )
    proto["audio_path"] = proto["filename"].astype(str).map(
        lambda x: str(audio_dir / f"{x}.flac")
    )
    proto["exists"] = proto["audio_path"].map(lambda p: Path(p).is_file())
    proto["split"] = split

    df = proto[proto["exists"] & proto["label"].isin(["bonafide", "spoof"])].copy()
    df["label_id"] = df["label"].map({"bonafide": 0, "spoof": 1}).astype(int)
    return df.reset_index(drop=True)


def balanced_subset(df: pd.DataFrame, per_class: int, seed: int = 42) -> pd.DataFrame:
    """
    Creates a class-balanced subset with `per_class` bona fide and `per_class` spoof samples.
    """
    parts = []
    for label in ["bonafide", "spoof"]:
        group = df[df["label"] == label]
        n = min(per_class, len(group))
        if n == 0:
            raise ValueError(f"No examples for class {label}")
        parts.append(group.sample(n=n, random_state=seed))
    combined = pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)
    return combined


class CachedAudioDataset(Dataset):
    """Dataset serving in-memory cached (N, 1, 64, 201) features."""

    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = X
        self.y = y

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        x_tensor = torch.from_numpy(np.array(self.X[idx], dtype=np.float32))
        y_val = int(self.y[idx])
        return x_tensor, y_val
