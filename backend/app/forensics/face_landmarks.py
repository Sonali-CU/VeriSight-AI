
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


# --------------------------------------------------
# Project configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "face_landmarker"
    / "face_landmarker.task"
)

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode


class FaceLandmarkAnalyzer:
    """
    Detect faces and extract facial landmarks from images
    or individual video frames.

    Input format: OpenCV BGR image (NumPy array).
    """

    def __init__(self, model_path=None, max_faces=5):

        self.model_path = Path(
            model_path or DEFAULT_MODEL_PATH
        )

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Face Landmarker model not found: {self.model_path}"
            )

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=str(self.model_path)
            ),
            running_mode=RunningMode.IMAGE,
            num_faces=max_faces,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.detector = FaceLandmarker.create_from_options(
            options
        )

    def analyze_frame(self, frame_bgr):
        """
        Analyse one BGR frame.

        Returns:
            Dictionary containing face count and
            landmark coordinates for each detected face.
        """

        if not isinstance(frame_bgr, np.ndarray):
            raise TypeError("Input must be a NumPy image array.")

        if frame_bgr.size == 0:
            raise ValueError("Input frame is empty.")

        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError("Expected a 3-channel BGR image.")

        height, width = frame_bgr.shape[:2]

        # Convert OpenCV BGR to RGB for MediaPipe.
        frame_rgb = cv2.cvtColor(
            frame_bgr,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb
        )

        result = self.detector.detect(mp_image)

        faces = []

        for face_landmarks in result.face_landmarks:

            points = []

            for landmark in face_landmarks:

                x = float(landmark.x * width)
                y = float(landmark.y * height)
                z = float(landmark.z)

                points.append({
                    "x": x,
                    "y": y,
                    "z": z,
                    "x_normalized": float(landmark.x),
                    "y_normalized": float(landmark.y)
                })

            # Calculate bounding box from landmark coordinates.
            xs = [point["x"] for point in points]
            ys = [point["y"] for point in points]

            x_min = max(0, int(min(xs)))
            y_min = max(0, int(min(ys)))
            x_max = min(width - 1, int(max(xs)))
            y_max = min(height - 1, int(max(ys)))

            faces.append({
                "landmark_count": len(points),
                "landmarks": points,
                "bounding_box": {
                    "x_min": x_min,
                    "y_min": y_min,
                    "x_max": x_max,
                    "y_max": y_max,
                    "width": x_max - x_min,
                    "height": y_max - y_min
                }
            })

        return {
            "face_detected": len(faces) > 0,
            "face_count": len(faces),
            "image_width": width,
            "image_height": height,
            "faces": faces
        }

    def close(self):
        """Release MediaPipe resources."""
        if self.detector is not None:
            self.detector.close()
            self.detector = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
