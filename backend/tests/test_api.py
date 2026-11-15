from io import BytesIO
from pathlib import Path
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def create_dummy_wav():
    """Generates a small in-memory 16 kHz mono WAV file for testing."""
    buf = BytesIO()
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    # 440 Hz tone
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.getvalue()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "verisight-api"
    assert data["status"] == "ok"
    assert "audio" in data["active_modalities"]


def test_models_endpoint():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    models = {m["modality"]: m for m in response.json()["models"]}
    assert len(models) == 4
    assert models["audio"]["status"] == "trained"
    assert models["image"]["status"] == "trained"
    assert models["video"]["status"] == "trained"
    assert models["fusion"]["status"] == "trained"


def test_audio_metrics_endpoint():
    response = client.get("/api/v1/audio/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["dataset"] == "ASVspoof 2019 LA"
    metrics = data["metrics"]
    assert "roc_auc" in metrics
    assert "eer_approx" in metrics
    assert "confusion_matrix" in metrics
    assert metrics["roc_auc"] > 0.80


def test_inspect_audio():
    wav_bytes = create_dummy_wav()
    response = client.post(
        "/api/v1/inspect",
        files={"file": ("synthetic_test.wav", wav_bytes, "audio/wav")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inspected"
    assert len(data["sha256"]) == 64
    assert data["metadata"]["channels"] == 1
    assert data["metadata"]["sample_rate"] == 16000


def test_audio_prediction_direct():
    wav_bytes = create_dummy_wav()
    response = client.post(
        "/api/v1/predict/audio",
        files={"file": ("tone.wav", wav_bytes, "audio/wav")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["modality"] == "audio"
    res = data["result"]
    assert res["verdict"] in {"REAL-LIKE", "SPOOF-LIKE", "INCONCLUSIVE"}
    assert "spoof_probability" in res
    assert "confidence" in res
    assert len(res["sha256"]) == 64
    assert "spectrogram_preview" in res


def test_audio_prediction_modality_route():
    wav_bytes = create_dummy_wav()
    response = client.post(
        "/api/v1/predict/audio",
        files={"file": ("tone.wav", wav_bytes, "audio/wav")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["model"] == "AudioSpoofCNN"


def test_unsupported_modality():
    response = client.post("/api/v1/predict/radar")
    assert response.status_code in {404, 422}
