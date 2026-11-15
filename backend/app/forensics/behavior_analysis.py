
import json
from pathlib import Path

import pandas as pd


def detect_blink_events(
    data,
    close_threshold=0.12,
    reopen_threshold=0.18,
    min_frames=2,
    max_blink_duration=0.50,
):
    """
    Detect candidate blink events using EAR hysteresis.

    A blink candidate starts when EAR falls below close_threshold
    and ends when EAR rises above reopen_threshold.

    These are behavioural measurements, not deepfake verdicts.
    """

    events = []
    active = False
    start_index = None

    for i, row in data.iterrows():
        ear = row["average_ear"]

        if pd.isna(ear):
            continue

        if not active and ear < close_threshold:
            active = True
            start_index = i

        elif active and ear > reopen_threshold:
            end_index = i - 1
            start_row = data.loc[start_index]
            end_row = data.loc[end_index]

            frame_count = end_index - start_index + 1
            duration = (
                end_row["timestamp_seconds"]
                - start_row["timestamp_seconds"]
                + 1 / data.attrs["fps"]
            )

            if frame_count >= min_frames:
                events.append({
                    "start_time": round(
                        float(start_row["timestamp_seconds"]), 3
                    ),
                    "end_time": round(
                        float(end_row["timestamp_seconds"]), 3
                    ),
                    "duration_seconds": round(float(duration), 3),
                    "frame_count": int(frame_count),
                    "minimum_ear": round(
                        float(data.loc[start_index:end_index, "average_ear"].min()),
                        4,
                    ),
                    "event_type": (
                        "candidate_blink"
                        if duration <= max_blink_duration
                        else "prolonged_eye_closure"
                    ),
                })

            active = False
            start_index = None

    # Handle a closure that continues until the video ends.
    if active and start_index is not None:
        end_index = data.index[-1]
        start_row = data.loc[start_index]
        end_row = data.loc[end_index]

        frame_count = end_index - start_index + 1
        duration = (
            end_row["timestamp_seconds"]
            - start_row["timestamp_seconds"]
            + 1 / data.attrs["fps"]
        )

        if frame_count >= min_frames:
            events.append({
                "start_time": round(float(start_row["timestamp_seconds"]), 3),
                "end_time": round(float(end_row["timestamp_seconds"]), 3),
                "duration_seconds": round(float(duration), 3),
                "frame_count": int(frame_count),
                "minimum_ear": round(
                    float(data.loc[start_index:end_index, "average_ear"].min()),
                    4,
                ),
                "event_type": "closure_at_video_end",
            })

    return events


def detect_mouth_activity(data, threshold=0.60, min_frames=2):
    """
    Detect periods of relatively high mouth opening using MAR.

    High MAR is not proof of speech. It can also reflect yawning,
    smiling, or other mouth movements.
    """

    active = False
    start_index = None
    events = []

    for i, row in data.iterrows():
        mar = row["mouth_aspect_ratio"]

        if pd.isna(mar):
            continue

        if not active and mar > threshold:
            active = True
            start_index = i

        elif active and mar <= threshold:
            end_index = i - 1
            start_row = data.loc[start_index]
            end_row = data.loc[end_index]
            frame_count = end_index - start_index + 1

            if frame_count >= min_frames:
                events.append({
                    "start_time": round(
                        float(start_row["timestamp_seconds"]), 3
                    ),
                    "end_time": round(
                        float(end_row["timestamp_seconds"]), 3
                    ),
                    "frame_count": int(frame_count),
                    "maximum_mar": round(
                        float(data.loc[start_index:end_index, "mouth_aspect_ratio"].max()),
                        4,
                    ),
                })

            active = False
            start_index = None

    if active and start_index is not None:
        end_index = data.index[-1]
        start_row = data.loc[start_index]
        end_row = data.loc[end_index]
        frame_count = end_index - start_index + 1

        if frame_count >= min_frames:
            events.append({
                "start_time": round(
                    float(start_row["timestamp_seconds"]), 3
                ),
                "end_time": round(
                    float(end_row["timestamp_seconds"]), 3
                ),
                "frame_count": int(frame_count),
                "maximum_mar": round(
                    float(data.loc[start_index:end_index, "mouth_aspect_ratio"].max()),
                    4,
                ),
            })

    return events


def analyze_behavior(csv_path):
    csv_path = Path(csv_path)

    data = pd.read_csv(csv_path)

    required_columns = {
        "timestamp_seconds",
        "average_ear",
        "mouth_aspect_ratio",
    }

    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    if len(data) < 2:
        raise ValueError("At least two frames are required.")

    data = data.sort_values("timestamp_seconds").reset_index(drop=True)

    time_diffs = data["timestamp_seconds"].diff().dropna()
    fps = 1 / time_diffs.median()

    data.attrs["fps"] = float(fps)

    duration = (
        float(data["timestamp_seconds"].iloc[-1])
        - float(data["timestamp_seconds"].iloc[0])
        + 1 / fps
    )

    blink_events = detect_blink_events(data)
    mouth_events = detect_mouth_activity(data)

    candidate_blinks = [
        event for event in blink_events
        if event["event_type"] == "candidate_blink"
    ]

    prolonged_closures = [
        event for event in blink_events
        if event["event_type"] == "prolonged_eye_closure"
    ]

    report = {
        "video_analysis": {
            "source_csv": csv_path.name,
            "total_frames": int(len(data)),
            "estimated_fps": round(float(fps), 2),
            "duration_seconds": round(duration, 2),
        },
        "eye_analysis": {
            "candidate_blink_count": len(candidate_blinks),
            "prolonged_closure_count": len(prolonged_closures),
            "blink_events": blink_events,
        },
        "mouth_analysis": {
            "high_mouth_activity_event_count": len(mouth_events),
            "mouth_events": mouth_events,
            "threshold_used": 0.60,
        },
        "interpretation": (
            "Behavioural measurements only. These results do not "
            "establish whether a video is real or manipulated."
        ),
    }

    output_path = csv_path.parent / "behavior_analysis_report.json"

    output_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    print("\nBEHAVIOURAL ANALYSIS COMPLETED")
    print("--------------------------------")
    print(f"Frames analysed: {len(data)}")
    print(f"Estimated FPS: {fps:.2f}")
    print(f"Video duration: {duration:.2f} seconds")
    print(f"Candidate blinks: {len(candidate_blinks)}")
    print(f"Prolonged closures: {len(prolonged_closures)}")
    print(f"High mouth activity events: {len(mouth_events)}")
    print(f"Report saved: {output_path}")

    return report


if __name__ == "__main__":
    analyze_behavior("test_video_facial_metrics.csv")
