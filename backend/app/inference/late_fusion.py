"""
Multimodal Late Fusion Engine for VeriSight AI.
Combines visual (CNN), temporal (BiLSTM), and acoustic (Log-Mel CNN) streams
using calibrated dynamic-weighted late fusion.
"""

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
import hashlib
import numpy as np
import soundfile as sf
import torch

from .image_detector import predict_image
from .video_detector import predict_video
from .temporal_video_detector import predict_temporal_video
from .audio_detector import predict_audio, get_audio_detector
from ..forensics.audio_preprocessing import probe_audio, extract_audio


def calibrate_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamps and normalizes probability scores to [0.0, 1.0]."""
    return float(np.clip(score, min_val, max_val))


class MultimodalLateFusionDetector:
    """
    Late fusion architecture combining unimodal evidence streams:
    - Visual frame score (EfficientNet-B0)
    - Temporal sequence dynamics (BiLSTM)
    - Acoustic spoof probability (AudioSpoofCNN)
    """

    def __init__(self, visual_weight: float = 0.35, temporal_weight: float = 0.35, audio_weight: float = 0.30):
        self.default_weights = {
            "visual": visual_weight,
            "temporal": temporal_weight,
            "audio": audio_weight
        }

    def fuse_scores(self, modalities: dict[str, float | None]) -> tuple[float, float, dict[str, float], str]:
        """
        Calculates normalized dynamic-weighted score across available modalities.
        Missing modalities are excluded and weights dynamically re-normalized.
        """
        active_weights = {}
        active_scores = {}

        for mod, score in modalities.items():
            if score is not None and not np.isnan(score):
                active_weights[mod] = self.default_weights.get(mod, 0.33)
                active_scores[mod] = score

        if not active_scores:
            return 0.5, 0.5, {}, "INCONCLUSIVE"

        # Re-normalize weights so they sum to 1.0
        total_weight = sum(active_weights.values())
        norm_weights = {m: w / total_weight for m, w in active_weights.items()}

        composite_spoof_score = sum(norm_weights[m] * active_scores[m] for m in active_scores)
        composite_real_score = 1.0 - composite_spoof_score

        # Calibrated decision boundary
        margin = 0.06
        if abs(composite_spoof_score - 0.50) < margin:
            verdict = "INCONCLUSIVE"
        elif composite_spoof_score >= 0.50:
            verdict = "SPOOF-LIKE"
        else:
            verdict = "REAL-LIKE"

        return composite_spoof_score, composite_real_score, norm_weights, verdict

    def analyze_multimodal_video(self, video_path: Path | str) -> dict:
        """
        Performs full end-to-end multimodal analysis on a video file:
        1. Temporal BiLSTM video analysis
        2. Frame-based visual analysis
        3. Audio stream extraction & AudioSpoofCNN analysis (if audio present)
        4. Late fusion combination
        """
        video_path = Path(video_path).resolve()
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        video_bytes = video_path.read_bytes()
        sha256_hash = hashlib.sha256(video_bytes).hexdigest()

        # 1. Temporal Video Detection
        temporal_result = predict_temporal_video(video_path)
        temporal_spoof_prob = temporal_result.get("fake_probability", 0.5)

        # 2. Frame-based Visual Detection
        frame_result = predict_video(video_bytes, video_path.name, max_frames=8)
        visual_spoof_prob = frame_result.get("fake_probability", 0.5)

        # 3. Audio Extraction & Analysis
        audio_info = probe_audio(video_path)
        audio_spoof_prob = None
        audio_result = None

        if audio_info is not None:
            try:
                extracted = extract_audio(video_path)
                audio_file_path = Path(extracted["audio"])
                if audio_file_path.is_file() and audio_file_path.stat().st_size > 0:
                    audio_bytes = audio_file_path.read_bytes()
                    audio_result = predict_audio(audio_bytes, audio_file_path.name)
                    audio_spoof_prob = audio_result.get("spoof_probability")
            except Exception as e:
                audio_result = {"status": "extraction_error", "error": str(e)}

        # 4. Late Fusion
        modality_inputs = {
            "visual": visual_spoof_prob,
            "temporal": temporal_spoof_prob,
            "audio": audio_spoof_prob
        }

        composite_spoof, composite_real, effective_weights, verdict = self.fuse_scores(modality_inputs)
        confidence = composite_spoof if verdict == "SPOOF-LIKE" else (composite_real if verdict == "REAL-LIKE" else 0.5)

        return {
            "verdict": verdict,
            "composite_spoof_probability": round(composite_spoof, 5),
            "composite_real_probability": round(composite_real, 5),
            "confidence": round(confidence, 5),
            "sha256": sha256_hash,
            "effective_weights": effective_weights,
            "modality_scores": {
                "visual_frame": round(visual_spoof_prob, 5),
                "temporal_sequence": round(temporal_spoof_prob, 5),
                "audio_spoof": round(audio_spoof_prob, 5) if audio_spoof_prob is not None else None
            },
            "sub_analyses": {
                "temporal": temporal_result,
                "visual_frames": frame_result,
                "audio": audio_result
            },
            "fusion_method": "Calibrated Dynamic-Weighted Late Fusion",
            "model": "VeriSight Multimodal Late Fusion",
            "warning": "Multimodal risk signal for forensic support; human verification required."
        }


_FUSION_DETECTOR = None


def get_fusion_detector() -> MultimodalLateFusionDetector:
    global _FUSION_DETECTOR
    if _FUSION_DETECTOR is None:
        _FUSION_DETECTOR = MultimodalLateFusionDetector()
    return _FUSION_DETECTOR


def predict_fusion(video_path: Path | str) -> dict:
    detector = get_fusion_detector()
    return detector.analyze_multimodal_video(video_path)
