
import cv2
import numpy as np

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image

from .image_detector import predict_image


def predict_video(
    video_bytes: bytes,
    filename: str,
    max_frames: int = 8
):
    """
    Performs frame-based deepfake detection on a video.

    Samples up to max_frames evenly distributed frames,
    predicts each frame using EfficientNet-B0, and averages
    the real/fake probabilities.
    """

    if not video_bytes:
        raise ValueError("Uploaded video is empty.")

    suffix = Path(filename).suffix.lower()

    if suffix not in {".mp4", ".mov", ".avi"}:
        raise ValueError("Unsupported video format.")

    if max_frames < 1:
        raise ValueError("max_frames must be at least 1.")

    temp_path = None
    capture = None

    try:
        with NamedTemporaryFile(
            suffix=suffix,
            delete=False
        ) as temp_file:
            temp_file.write(video_bytes)
            temp_path = temp_file.name

        capture = cv2.VideoCapture(temp_path)

        if not capture.isOpened():
            raise ValueError("Unable to open the uploaded video.")

        total_frames = int(
            capture.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        if total_frames <= 0:
            raise ValueError("Video contains no readable frames.")

        sample_count = min(max_frames, total_frames)

        frame_indices = np.linspace(
            0,
            total_frames - 1,
            num=sample_count,
            dtype=int
        )

        frame_results = []

        for frame_index in frame_indices:
            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                int(frame_index)
            )

            success, frame = capture.read()

            if not success:
                continue

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            image = Image.fromarray(rgb_frame)

            result = predict_image(image)

            frame_results.append({
                "frame_number": int(frame_index),
                "prediction": result["prediction"],
                "real_probability": float(
                    result["real_probability"]
                ),
                "fake_probability": float(
                    result["fake_probability"]
                )
            })

        if not frame_results:
            raise ValueError("Could not extract any readable video frames.")

        average_real = float(
            np.mean([
                item["real_probability"]
                for item in frame_results
            ])
        )

        average_fake = float(
            np.mean([
                item["fake_probability"]
                for item in frame_results
            ])
        )

        prediction = (
            "fake" if average_fake >= 0.5 else "real"
        )

        return {
            "prediction": prediction,
            "real_probability": average_real,
            "fake_probability": average_fake,
            "model": "EfficientNet-B0",
            "analysis_method": "Frame-based probability aggregation",
            "total_video_frames": total_frames,
            "sampled_frames": len(frame_results),
            "frame_results": frame_results
        }

    finally:
        if capture is not None:
            capture.release()

        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
