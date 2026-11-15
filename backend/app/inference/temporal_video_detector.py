
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

IMAGE_CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "models"
    / "image"
    / "verisight_efficientnet_b0_ffpp_source_disjoint.pth"
)

TEMPORAL_CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "models"
    / "video"
    / "verisight_temporal_lstm_best.pth"
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

SEQUENCE_LENGTH = 16
IMAGE_SIZE = 224
FEATURE_DIMENSION = 1280

IMAGE_MEAN = (0.485, 0.456, 0.406)
IMAGE_STD = (0.229, 0.224, 0.225)


# ============================================================
# TEMPORAL MODEL
# Must match the trained Colab architecture
# ============================================================

class TemporalLSTM(nn.Module):

    def __init__(self):
        super().__init__()

        self.projection = nn.Sequential(
            nn.Linear(1280, 256),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        self.lstm = nn.LSTM(
            input_size=256,
            hidden_size=64,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )

        self.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(128, 1)
        )

    def forward(self, x):

        x = self.projection(x)

        x, _ = self.lstm(x)

        x = x.mean(dim=1)

        return self.classifier(x).squeeze(1)


# ============================================================
# LOAD IMAGE FEATURE EXTRACTOR
# ============================================================

def load_feature_extractor():

    if not IMAGE_CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(
            f"Image checkpoint not found: {IMAGE_CHECKPOINT_PATH}"
        )

    checkpoint = torch.load(
        IMAGE_CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=False
    )

    backbone = models.efficientnet_b0(weights=None)

    # Match the two-class trained checkpoint.
    backbone.classifier[1] = nn.Linear(1280, 2)

    backbone.load_state_dict(
        checkpoint["state_dict"],
        strict=True
    )

    feature_extractor = nn.Sequential(
        backbone.features,
        backbone.avgpool,
        nn.Flatten(1)
    )

    feature_extractor = feature_extractor.to(DEVICE)
    feature_extractor.eval()

    for parameter in feature_extractor.parameters():
        parameter.requires_grad = False

    mean = torch.tensor(
        checkpoint["mean"],
        dtype=torch.float32,
        device=DEVICE
    ).view(1, 3, 1, 1)

    std = torch.tensor(
        checkpoint["std"],
        dtype=torch.float32,
        device=DEVICE
    ).view(1, 3, 1, 1)

    return feature_extractor, mean, std


# ============================================================
# LOAD TEMPORAL CLASSIFIER
# ============================================================

def load_temporal_classifier():

    if not TEMPORAL_CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(
            f"Temporal checkpoint not found: "
            f"{TEMPORAL_CHECKPOINT_PATH}"
        )

    checkpoint = torch.load(
        TEMPORAL_CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=False
    )

    if checkpoint.get("sequence_length") != SEQUENCE_LENGTH:
        raise ValueError(
            "Checkpoint sequence length does not match inference."
        )

    if checkpoint.get("input_size") != FEATURE_DIMENSION:
        raise ValueError(
            "Checkpoint feature dimension does not match inference."
        )

    if checkpoint.get("class_to_label") != {
        "real": 0,
        "fake": 1
    }:
        raise ValueError(
            "Unexpected class mapping in temporal checkpoint."
        )

    temporal_model = TemporalLSTM()

    temporal_model.load_state_dict(
        checkpoint["model_state_dict"],
        strict=True
    )

    temporal_model = temporal_model.to(DEVICE)
    temporal_model.eval()

    feature_mean = torch.as_tensor(
        checkpoint["feature_mean"],
        dtype=torch.float32,
        device=DEVICE
    ).reshape(1, 1, FEATURE_DIMENSION)

    feature_std = torch.as_tensor(
        checkpoint["feature_std"],
        dtype=torch.float32,
        device=DEVICE
    ).reshape(1, 1, FEATURE_DIMENSION)

    if torch.any(feature_std <= 0):
        raise ValueError(
            "Invalid feature standard deviation in checkpoint."
        )

    return temporal_model, feature_mean, feature_std


# ============================================================
# INITIALIZE MODELS
# ============================================================

FEATURE_EXTRACTOR, IMAGE_MEAN_TENSOR, IMAGE_STD_TENSOR = (
    load_feature_extractor()
)

TEMPORAL_MODEL, FEATURE_MEAN, FEATURE_STD = (
    load_temporal_classifier()
)


# ============================================================
# VIDEO FRAME EXTRACTION
# 16 consecutive frames from the centre
# ============================================================

def extract_video_frames(video_path):

    video_path = Path(video_path)

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ValueError("Unable to open uploaded video.")

    try:

        total_frames = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        if total_frames < SEQUENCE_LENGTH:
            raise ValueError(
                "Video must contain at least 16 readable frames."
            )

        start_frame = (
            total_frames - SEQUENCE_LENGTH
        ) // 2

        cap.set(
            cv2.CAP_PROP_POS_FRAMES,
            start_frame
        )

        frames = []

        for _ in range(SEQUENCE_LENGTH):

            success, frame = cap.read()

            if not success:
                raise ValueError(
                    "Unable to extract all 16 video frames."
                )

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            frame = cv2.resize(
                frame,
                (IMAGE_SIZE, IMAGE_SIZE),
                interpolation=cv2.INTER_AREA
            )

            frames.append(frame)

        return np.stack(frames)

    finally:
        cap.release()


# ============================================================
# TEMPORAL VIDEO PREDICTION
# ============================================================

def predict_temporal_video(video_path):

    frames = extract_video_frames(video_path)

    if frames.shape != (16, 224, 224, 3):
        raise ValueError(
            f"Unexpected frame sequence shape: {frames.shape}"
        )

    x = torch.from_numpy(frames).to(DEVICE)

    x = x.permute(0, 3, 1, 2).float() / 255.0

    x = (
        x - IMAGE_MEAN_TENSOR
    ) / IMAGE_STD_TENSOR

    with torch.inference_mode():

        # Extract 16 EfficientNet feature vectors.
        frame_features = FEATURE_EXTRACTOR(x)

        if frame_features.shape != (16, 1280):
            raise ValueError(
                "Unexpected EfficientNet feature dimensions."
            )

        # Add batch dimension.
        temporal_features = frame_features.unsqueeze(0)

        # Apply training-time feature normalization.
        temporal_features = (
            temporal_features - FEATURE_MEAN
        ) / FEATURE_STD

        # Predict fake-class logit.
        logits = TEMPORAL_MODEL(temporal_features)

        fake_probability = torch.sigmoid(logits).item()

    real_probability = 1.0 - fake_probability

    prediction = (
        "FAKE"
        if fake_probability >= 0.5
        else "REAL"
    )

    confidence = max(
        fake_probability,
        real_probability
    )

    return {
        "prediction": prediction,
        "real_probability": round(real_probability, 6),
        "fake_probability": round(fake_probability, 6),
        "confidence": round(confidence, 6),
        "frames_analyzed": SEQUENCE_LENGTH,
        "model": "EfficientNet-B0 + BiLSTM",
        "analysis_method": "Temporal feature sequence classification",
        "device": str(DEVICE)
    }
