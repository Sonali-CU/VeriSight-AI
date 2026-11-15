from PIL import Image, UnidentifiedImageError
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import aiofiles
import soundfile as sf

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import UPLOAD_DIR, MAX_UPLOAD_MB, ALLOWED_EXTENSIONS, PROJECT_ROOT
from .model_registry import modality_status, read_registry
from .inference.image_detector import predict_image
from .inference.video_detector import predict_video
from .inference.temporal_video_detector import predict_temporal_video
from .inference.audio_detector import predict_audio
from .inference.late_fusion import predict_fusion


app = FastAPI(
    title="VeriSight AI API",
    description=(
        "Multimodal cybersecurity deepfake forensic platform with image, "
        "frame-based video, temporal BiLSTM video, and CPU-compatible ASVspoof 2019 LA audio inference."
    ),
    version="2.2.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    registry = read_registry()

    trained = any(
        v.get("status") == "trained"
        for v in registry.values()
    )

    return {
        "status": "ok",
        "service": "verisight-api",
        "model_status": (
            "models_active" if trained else "not_trained"
        ),
        "active_modalities": [
            k for k, v in registry.items() if v.get("status") == "trained"
        ]
    }


@app.get("/api/v1/models")
async def models():
    return {
        "models": [
            modality_status(m)
            for m in ("image", "video", "audio", "fusion")
        ]
    }


@app.get("/api/v1/audio/metrics")
async def audio_metrics():
    """Returns genuine ASVspoof 2019 LA training & evaluation metrics, confusion matrix, and history."""
    audio_dir = PROJECT_ROOT / "models" / "audio"
    metrics_path = audio_dir / "audio_dev_metrics.json"
    metadata_path = audio_dir / "verisight_audio_cnn_metadata.json"
    history_path = audio_dir / "audio_training_history.csv"

    if not metrics_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Audio model metrics not found. Train the model first."
        )

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metadata = {}
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    history = []
    if history_path.is_file():
        import pandas as pd
        history = pd.read_csv(history_path).to_dict(orient="records")

    return {
        "status": "success",
        "model_name": metadata.get("model_name", "VeriSight AI Audio Spoof CNN"),
        "dataset": metadata.get("dataset", "ASVspoof 2019 LA"),
        "architecture": metadata.get("architecture", "AudioSpoofCNN"),
        "metrics": metrics,
        "history": history,
        "limitations": metadata.get("limitations", [])
    }


@app.post("/api/v1/inspect")
async def inspect_media(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension: {suffix}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    limit = MAX_UPLOAD_MB * 1024 * 1024
    token = uuid4().hex
    target = UPLOAD_DIR / f"{token}{suffix}"

    digest = hashlib.sha256()
    size = 0
    buffer = bytearray()

    try:
        async with aiofiles.open(target, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {MAX_UPLOAD_MB} MB limit."
                    )
                digest.update(chunk)
                buffer.extend(chunk)
                await out.write(chunk)

        # Extract extra format-specific metadata
        meta = {}
        if suffix in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}:
            try:
                info = sf.info(BytesIO(buffer))
                meta = {
                    "audio_format": info.format,
                    "audio_subtype": info.subtype,
                    "channels": info.channels,
                    "sample_rate": info.samplerate,
                    "duration_seconds": round(info.duration, 3)
                }
            except Exception:
                pass
        elif suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            try:
                img = Image.open(BytesIO(buffer))
                meta = {
                    "image_dimensions": [img.width, img.height],
                    "image_format": img.format,
                    "color_mode": img.mode
                }
            except Exception:
                pass

        return {
            "status": "inspected",
            "filename": Path(file.filename or "upload").name,
            "bytes": size,
            "sha256": digest.hexdigest(),
            "metadata": meta,
            "prediction": None,
            "message": (
                "Inspection completed. Cryptographic hash verified. "
                "No authenticity prediction was made."
            ),
            "upload_id": token
        }

    except Exception:
        target.unlink(missing_ok=True)
        raise

    finally:
        await file.close()


@app.post("/api/v1/predict/audio")
async def predict_audio_endpoint(file: UploadFile = File(...)):
    """Direct dedicated endpoint for audio deepfake detection."""
    suffix = Path(file.filename or "").suffix.lower()
    audio_extensions = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}

    if suffix not in audio_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {suffix}. Supported: WAV, MP3, FLAC, M4A."
        )

    try:
        limit = MAX_UPLOAD_MB * 1024 * 1024
        contents = await file.read(limit + 1)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio file is empty."
            )

        if len(contents) > limit:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {MAX_UPLOAD_MB} MB limit."
            )

        result = predict_audio(contents, Path(file.filename or "upload.wav").name)

        return {
            "status": "success",
            "filename": Path(file.filename or "upload").name,
            "modality": "audio",
            "result": result
        }

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    finally:
        await file.close()


@app.post("/api/v1/predict/{modality}")
async def predict(
    modality: str,
    file: UploadFile = File(...)
):
    if modality not in {"image", "video", "audio", "fusion"}:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown modality: {modality}."
        )

    suffix = Path(file.filename or "").suffix.lower()
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    video_extensions = {".mp4", ".mov", ".avi"}
    audio_extensions = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}

    if modality == "image" and suffix not in image_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image format: {suffix}. Supported: JPG, JPEG, PNG, WEBP."
        )

    if (modality in {"video", "fusion"}) and suffix not in video_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported video/fusion format: {suffix}. Supported: MP4, MOV, AVI."
        )

    if modality == "audio" and suffix not in audio_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {suffix}. Supported: WAV, MP3, FLAC, M4A."
        )

    temp_target = None
    try:
        limit = MAX_UPLOAD_MB * 1024 * 1024
        contents = await file.read(limit + 1)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        if len(contents) > limit:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {MAX_UPLOAD_MB} MB limit."
            )

        if modality == "image":
            try:
                image = Image.open(BytesIO(contents))
                image.load()
            except (UnidentifiedImageError, OSError):
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is not a valid image."
                )
            result = predict_image(image)

        elif modality == "video":
            result = predict_video(
                video_bytes=contents,
                filename=Path(file.filename or "upload.mp4").name,
                max_frames=8
            )

        elif modality == "audio":
            result = predict_audio(
                audio_bytes=contents,
                filename=Path(file.filename or "upload.wav").name
            )

        else:  # fusion
            temp_target = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
            temp_target.write_bytes(contents)
            result = predict_fusion(temp_target)

        return {
            "status": "success",
            "filename": Path(file.filename or "upload").name,
            "modality": modality,
            "result": result
        }

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    finally:
        if temp_target is not None:
            temp_target.unlink(missing_ok=True)
        await file.close()


@app.post("/api/v1/predict/video/temporal")
async def predict_temporal(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    video_extensions = {".mp4", ".mov", ".avi"}

    if suffix not in video_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported video format: {suffix}. Use MP4, MOV or AVI."
        )

    target = UPLOAD_DIR / f"{uuid4().hex}{suffix}"

    try:
        limit = MAX_UPLOAD_MB * 1024 * 1024
        contents = await file.read(limit + 1)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded video is empty."
            )

        if len(contents) > limit:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {MAX_UPLOAD_MB} MB limit."
            )

        target.write_bytes(contents)
        result = predict_temporal_video(target)

        return {
            "status": "success",
            "filename": Path(file.filename or "upload").name,
            "modality": "video",
            "model_type": "temporal",
            "result": result
        }

    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    finally:
        target.unlink(missing_ok=True)
        await file.close()
