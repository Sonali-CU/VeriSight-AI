from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = Path(os.getenv("VERISIGHT_UPLOAD_DIR", PROJECT_ROOT / "runtime" / "uploads"))
MAX_UPLOAD_MB = int(os.getenv("VERISIGHT_MAX_UPLOAD_MB", "200"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi", ".wav", ".mp3", ".flac", ".m4a"}
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
