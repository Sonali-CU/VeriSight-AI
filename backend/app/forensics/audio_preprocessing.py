
from pathlib import Path
import json
import shutil
import subprocess


class AudioExtractionError(Exception):
    """Raised when audio extraction or validation fails."""


def _run(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise AudioExtractionError(
            result.stderr.strip() or "External command failed."
        )

    return result.stdout.strip()


def probe_audio(video_path):
    """Return audio stream metadata, or None if no audio exists."""

    video_path = Path(video_path).resolve()

    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise AudioExtractionError("ffprobe was not found in PATH.")

    output = _run([
        ffprobe,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels,duration",
        "-of", "json",
        str(video_path)
    ])

    data = json.loads(output)
    streams = data.get("streams", [])

    if not streams:
        return None

    stream = streams[0]

    return {
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream["sample_rate"])
        if stream.get("sample_rate") else None,
        "channels": int(stream["channels"])
        if stream.get("channels") else None,
        "duration_seconds": float(stream["duration"])
        if stream.get("duration") else None
    }


def extract_audio(video_path, output_path=None, sample_rate=16000):
    """
    Extract the first audio stream as mono PCM WAV.

    Returns extraction metadata.
    """

    video_path = Path(video_path).resolve()

    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive.")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioExtractionError("ffmpeg was not found in PATH.")

    audio_info = probe_audio(video_path)

    if audio_info is None:
        raise AudioExtractionError(
            "This video does not contain an audio stream."
        )

    if output_path is None:
        project_root = Path(__file__).resolve().parents[3]
        output_dir = project_root / "forensics_output" / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}_audio_16k.wav"
    else:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-v", "error",
        "-i", str(video_path),
        "-map", "0:a:0",
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(output_path)
    ]

    _run(command)

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise AudioExtractionError("Extracted audio file is empty.")

    import soundfile as sf

    audio, actual_sample_rate = sf.read(
        str(output_path),
        dtype="float32"
    )

    if audio.ndim != 1:
        raise AudioExtractionError("Expected mono audio.")

    if actual_sample_rate != sample_rate:
        raise AudioExtractionError(
            f"Expected {sample_rate} Hz, got {actual_sample_rate} Hz."
        )

    return {
        "video": str(video_path),
        "audio": str(output_path),
        "source_audio": audio_info,
        "sample_rate": actual_sample_rate,
        "channels": 1,
        "duration_seconds": round(len(audio) / actual_sample_rate, 3),
        "samples": len(audio),
        "file_size_bytes": output_path.stat().st_size,
        "format": "WAV PCM 16-bit",
        "status": "success"
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract and validate audio from a video."
    )
    parser.add_argument("video", help="Input video path")
    parser.add_argument("--output", help="Optional output WAV path")
    args = parser.parse_args()

    try:
        result = extract_audio(args.video, args.output)
        print(json.dumps(result, indent=4))
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
