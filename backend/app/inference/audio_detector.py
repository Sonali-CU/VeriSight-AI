"""
Inference module for VeriSight AI Audio Deepfake Detector.
Supports WAV, MP3, FLAC, M4A audio formats on CPU.
Extracts audio metadata, computes SHA-256 integrity hash,
generates spectrogram telemetry, and computes deepfake risk.
"""

from io import BytesIO
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
import torchaudio

from ..config import PROJECT_ROOT
from ..audio.model import AudioSpoofCNN

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "models"
    / "audio"
    / "verisight_audio_cnn_cpu.pth"
)

DEVICE = torch.device("cpu")

_DETECTOR = None


class VeriSightAudioDetector:
    """Production CPU-only audio deepfake detector."""

    def __init__(self, checkpoint_path: Path = CHECKPOINT_PATH):
        self.device = DEVICE
        if not checkpoint_path.is_file():
            raise FileNotFoundError(
                f"Audio model checkpoint not found at: {checkpoint_path}. "
                "Please ensure the audio model has been trained."
            )

        ckpt = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model = AudioSpoofCNN().to(self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()

        self.threshold = float(ckpt.get("threshold", 0.5))
        self.sr = int(ckpt.get("sample_rate", 16000))
        self.duration_sec = int(ckpt.get("duration_sec", 2))
        self.target_samples = self.sr * self.duration_sec
        self.n_fft = int(ckpt.get("n_fft", 512))
        self.hop_length = int(ckpt.get("hop_length", 160))
        self.n_mels = int(ckpt.get("n_mels", 64))

        self.transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=self.sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels,
            power=2.0
        )

    def load_audio(self, audio_source: str | Path | bytes | BytesIO) -> tuple[np.ndarray, int, dict]:
        """Loads audio stream or bytes and returns raw float32 array, sample rate, and metadata."""
        if isinstance(audio_source, (bytes, bytearray)):
            file_obj = BytesIO(audio_source)
        elif isinstance(audio_source, (str, Path)):
            file_obj = str(audio_source)
        else:
            file_obj = audio_source

        # Extract soundfile info
        try:
            info = sf.info(file_obj)
            format_name = info.format
            subtype_name = info.subtype
            channels = info.channels
            duration = info.duration
            raw_sr = info.samplerate
        except Exception:
            format_name = "UNKNOWN"
            subtype_name = "UNKNOWN"
            channels = 1
            duration = 0.0
            raw_sr = 16000

        # Reset pointer if BytesIO
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        audio, sr = sf.read(file_obj, dtype="float32")
        if audio.ndim == 2:
            audio = audio.mean(axis=1)

        audio = np.nan_to_num(audio, copy=False)
        duration = float(len(audio) / sr) if sr > 0 else duration

        metadata = {
            "format": format_name,
            "subtype": subtype_name,
            "channels": channels,
            "sample_rate": sr,
            "samples": len(audio),
            "duration_seconds": round(duration, 3)
        }
        return audio, sr, metadata

    def extract_features(self, audio: np.ndarray, sr: int) -> tuple[torch.Tensor, np.ndarray]:
        """Preprocesses audio into fixed tensor and normalized Log-Mel spectrogram."""
        x = torch.from_numpy(np.asarray(audio, dtype=np.float32))

        if sr != self.sr:
            x = torchaudio.functional.resample(x, orig_freq=sr, new_freq=self.sr)

        # Fixed crop or pad
        if x.numel() > self.target_samples:
            x = x[:self.target_samples]
        elif x.numel() < self.target_samples:
            x = F.pad(x, (0, self.target_samples - x.numel()))

        with torch.no_grad():
            mel = self.transform(x.unsqueeze(0))
            logmel = torch.log(mel + 1e-6)
            norm_logmel = (logmel - logmel.mean()) / (logmel.std() + 1e-5)

        return norm_logmel.unsqueeze(0).to(self.device), norm_logmel.squeeze(0).cpu().numpy()

    def compute_acoustic_features(self, audio: np.ndarray, sr: int) -> dict:
        """Computes lightweight forensic acoustic metrics without heavy dependencies."""
        if len(audio) == 0:
            return {"rms": 0.0, "zero_crossing_rate": 0.0, "spectral_centroid_approx": 0.0}

        # RMS Energy
        rms = float(np.sqrt(np.mean(np.square(audio))))

        # Zero crossing rate
        signs = np.sign(audio)
        crossings = np.sum(np.abs(signs[1:] - signs[:-1]) > 0)
        zcr = float(crossings / max(1, len(audio)))

        # Approximate spectral centroid from FFT
        fft_vals = np.abs(np.fft.rfft(audio[:min(len(audio), sr * 2)]))
        freqs = np.fft.rfftfreq(min(len(audio), sr * 2), 1.0 / sr)
        sum_fft = np.sum(fft_vals)
        centroid = float(np.sum(freqs * fft_vals) / max(1e-9, sum_fft))

        return {
            "rms": round(rms, 5),
            "zero_crossing_rate": round(zcr, 5),
            "spectral_centroid_approx_hz": round(centroid, 1)
        }

    def predict(self, audio_bytes: bytes, filename: str) -> dict:
        """Performs full end-to-end inference on uploaded audio bytes."""
        sha256_hash = hashlib.sha256(audio_bytes).hexdigest()
        file_size = len(audio_bytes)

        audio, sr, meta = self.load_audio(BytesIO(audio_bytes))
        meta["file_size_bytes"] = file_size
        meta["filename"] = filename

        input_tensor, logmel_matrix = self.extract_features(audio, sr)

        with torch.no_grad():
            logits = self.model(input_tensor)
            probs = torch.softmax(logits, dim=1)[0]
            bonafide_prob = float(probs[0].item())
            spoof_prob = float(probs[1].item())

        # Determine verdict with confidence margin around decision threshold
        margin = min(0.015, abs(1.0 - self.threshold) / 3.0)
        if abs(spoof_prob - self.threshold) <= margin:
            verdict = "INCONCLUSIVE"
            prediction = "inconclusive"
            risk_level = "MODERATE"
            confidence = 0.50
        elif spoof_prob > self.threshold:
            verdict = "SPOOF-LIKE"
            prediction = "fake"
            risk_level = "HIGH"
            confidence = spoof_prob
        else:
            verdict = "REAL-LIKE"
            prediction = "real"
            risk_level = "LOW"
            confidence = bonafide_prob

        acoustic = self.compute_acoustic_features(audio, sr)

        # Downsample spectrogram matrix to a compact grid (32 bands x 50 time steps) for frontend 3D rendering
        h, w = logmel_matrix.shape
        step_w = max(1, w // 50)
        step_h = max(1, h // 32)
        downsampled = logmel_matrix[::step_h, ::step_w].tolist()

        return {
            "verdict": verdict,
            "prediction": prediction,
            "risk_level": risk_level,
            "spoof_probability": round(spoof_prob, 5),
            "real_probability": round(bonafide_prob, 5),
            "confidence": round(confidence, 5),
            "decision_threshold": round(self.threshold, 4),
            "sha256": sha256_hash,
            "metadata": meta,
            "acoustic_features": acoustic,
            "spectrogram_preview": {
                "shape": [len(downsampled), len(downsampled[0]) if downsampled else 0],
                "data": downsampled
            },
            "model": "AudioSpoofCNN",
            "analysis_method": "ASVspoof 2019 LA Normalized Log-Mel 2D-CNN",
            "device": "CPU",
            "warning": "Audio deepfake estimate only; not forensic proof. Human verification is required."
        }


def get_audio_detector() -> VeriSightAudioDetector:
    """Cached singleton instance of the detector."""
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = VeriSightAudioDetector()
    return _DETECTOR


def predict_audio(audio_bytes: bytes, filename: str) -> dict:
    """Convenience functional wrapper for FastAPI endpoint."""
    detector = get_audio_detector()
    return detector.predict(audio_bytes, filename)
