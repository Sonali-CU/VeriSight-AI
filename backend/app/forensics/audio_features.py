from pathlib import Path
import json

import librosa
import numpy as np
import soundfile as sf


def extract_audio_features(
    audio_path,
    output_dir=None,
    sample_rate=16000,
    n_mfcc=40,
    n_mels=80
):
    """
    Extract acoustic features from a mono WAV file.

    Saves:
      - MFCC features
      - Log-Mel spectrogram
      - Spectral features
      - Audio metadata
    """

    audio_path = Path(audio_path).resolve()

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio, sr = sf.read(str(audio_path), dtype="float32")

    if audio.ndim != 1:
        raise ValueError("Expected mono audio.")

    if sr != sample_rate:
        raise ValueError(
            f"Expected {sample_rate} Hz audio, received {sr} Hz."
        )

    if len(audio) == 0:
        raise ValueError("Audio file is empty.")

    if not np.all(np.isfinite(audio)):
        raise ValueError("Audio contains invalid numerical values.")

    # MFCC features
    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sr,
        n_mfcc=n_mfcc,
        n_fft=512,
        hop_length=160
    )

    # Log-Mel spectrogram
    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160,
        n_mels=n_mels,
        power=2.0
    )

    log_mel = librosa.power_to_db(
        mel,
        ref=np.max
    )

    # Spectral features
    spectral_centroid = librosa.feature.spectral_centroid(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160
    )

    spectral_bandwidth = librosa.feature.spectral_bandwidth(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160
    )

    spectral_rolloff = librosa.feature.spectral_rolloff(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160
    )

    zero_crossing_rate = librosa.feature.zero_crossing_rate(
        y=audio,
        frame_length=512,
        hop_length=160
    )

    rms = librosa.feature.rms(
        y=audio,
        frame_length=512,
        hop_length=160
    )

    # Output directory
    if output_dir is None:
        project_root = Path(__file__).resolve().parents[3]
        output_dir = (
            project_root
            / "forensics_output"
            / "audio_features"
        )
    else:
        output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = audio_path.stem

    # Save numerical features
    feature_file = output_dir / f"{prefix}_features.npz"

    np.savez_compressed(
        feature_file,
        mfcc=mfcc.astype(np.float32),
        log_mel=log_mel.astype(np.float32),
        spectral_centroid=spectral_centroid.astype(np.float32),
        spectral_bandwidth=spectral_bandwidth.astype(np.float32),
        spectral_rolloff=spectral_rolloff.astype(np.float32),
        zero_crossing_rate=zero_crossing_rate.astype(np.float32),
        rms=rms.astype(np.float32)
    )

    # Metadata
    metadata = {
        "audio_file": str(audio_path),
        "sample_rate": sr,
        "duration_seconds": round(len(audio) / sr, 3),
        "samples": len(audio),
        "mfcc_shape": list(mfcc.shape),
        "log_mel_shape": list(log_mel.shape),
        "spectral_centroid_shape": list(spectral_centroid.shape),
        "spectral_bandwidth_shape": list(spectral_bandwidth.shape),
        "spectral_rolloff_shape": list(spectral_rolloff.shape),
        "zero_crossing_rate_shape": list(zero_crossing_rate.shape),
        "rms_shape": list(rms.shape),
        "mean_rms": float(np.mean(rms)),
        "mean_spectral_centroid": float(np.mean(spectral_centroid)),
        "mean_zero_crossing_rate": float(np.mean(zero_crossing_rate)),
        "feature_file": str(feature_file),
        "status": "success"
    }

    metadata_file = output_dir / f"{prefix}_metadata.json"

    with open(metadata_file, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

    return metadata


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract audio forensic features."
    )

    parser.add_argument("audio", help="Input mono WAV file")

    args = parser.parse_args()

    try:
        result = extract_audio_features(args.audio)
        print(json.dumps(result, indent=4))

    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)