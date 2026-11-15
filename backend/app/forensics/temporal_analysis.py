
import argparse
import csv
from pathlib import Path

import cv2

from backend.app.forensics.face_landmarks import FaceLandmarkAnalyzer
from backend.app.forensics.facial_metrics import FacialMetricsAnalyzer


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def analyze_video(video_path, output_csv=None, max_width=960):
    """
    Extract facial EAR and MAR measurements from every video frame.

    If multiple faces are detected, analyse the largest face.
    Saves timestamped measurements to a CSV file.
    """

    video_path = Path(video_path)

    if not video_path.is_absolute():
        video_path = PROJECT_ROOT / video_path

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    if output_csv is None:
        output_csv = video_path.with_name(
            video_path.stem + "_facial_metrics.csv"
        )
    else:
        output_csv = Path(output_csv)

        if not output_csv.is_absolute():
            output_csv = PROJECT_ROOT / output_csv

    output_csv.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(
            f"Could not open video: {video_path}"
        )

    fps = capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(
        capture.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    if fps <= 0:
        capture.release()
        raise ValueError("Invalid video FPS.")

    metrics_analyzer = FacialMetricsAnalyzer()

    fieldnames = [
        "frame_index",
        "timestamp_seconds",
        "face_detected",
        "face_count",
        "left_eye_ear",
        "right_eye_ear",
        "average_ear",
        "mouth_aspect_ratio"
    ]

    processed_frames = 0
    detected_frames = 0

    try:
        with FaceLandmarkAnalyzer() as face_detector:

            with open(
                output_csv,
                "w",
                newline="",
                encoding="utf-8"
            ) as csv_file:

                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=fieldnames
                )

                writer.writeheader()

                while True:

                    success, frame = capture.read()

                    if not success:
                        break

                    frame_index = processed_frames

                    timestamp = frame_index / fps

                    height, width = frame.shape[:2]

                    # Resize large frames to reduce CPU processing time.
                    if width > max_width:

                        scale = max_width / width

                        new_width = max_width
                        new_height = int(height * scale)

                        frame = cv2.resize(
                            frame,
                            (new_width, new_height),
                            interpolation=cv2.INTER_AREA
                        )

                    # Extract facial landmarks.
                    face_result = face_detector.analyze_frame(
                        frame
                    )

                    face_count = face_result["face_count"]

                    row = {
                        "frame_index": frame_index,
                        "timestamp_seconds": round(timestamp, 4),
                        "face_detected": face_count > 0,
                        "face_count": face_count,
                        "left_eye_ear": "",
                        "right_eye_ear": "",
                        "average_ear": "",
                        "mouth_aspect_ratio": ""
                    }

                    if face_count > 0:

                        # Select the largest detected face.
                        largest_face = max(
                            face_result["faces"],
                            key=lambda face: (
                                face["bounding_box"]["width"]
                                * face["bounding_box"]["height"]
                            )
                        )

                        metrics = metrics_analyzer.analyze_face(
                            largest_face
                        )

                        row.update({
                            "left_eye_ear": (
                                round(metrics["left_eye_ear"], 6)
                                if metrics["left_eye_ear"] is not None
                                else ""
                            ),
                            "right_eye_ear": (
                                round(metrics["right_eye_ear"], 6)
                                if metrics["right_eye_ear"] is not None
                                else ""
                            ),
                            "average_ear": (
                                round(metrics["average_ear"], 6)
                                if metrics["average_ear"] is not None
                                else ""
                            ),
                            "mouth_aspect_ratio": (
                                round(metrics["mouth_aspect_ratio"], 6)
                                if metrics["mouth_aspect_ratio"] is not None
                                else ""
                            )
                        })

                        detected_frames += 1

                    writer.writerow(row)

                    processed_frames += 1

                    if processed_frames % 100 == 0:
                        print(
                            f"Processed {processed_frames}/{total_frames} frames"
                        )

    finally:
        capture.release()

    print("\nTEMPORAL FACIAL ANALYSIS COMPLETED")
    print("----------------------------------")
    print("Video:", video_path.name)
    print("FPS:", round(fps, 2))
    print("Total frames:", total_frames)
    print("Processed frames:", processed_frames)
    print("Frames with detected faces:", detected_frames)
    print(
        "Face detection rate:",
        round(
            detected_frames / processed_frames * 100,
            2
        ) if processed_frames else 0,
        "%"
    )
    print("CSV saved:", output_csv)

    return output_csv


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="VeriSight AI Temporal Facial Analysis"
    )

    parser.add_argument(
        "video",
        help="Path to the input video"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional output CSV path"
    )

    args = parser.parse_args()

    analyze_video(
        video_path=args.video,
        output_csv=args.output
    )
