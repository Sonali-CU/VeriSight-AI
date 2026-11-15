
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parents[3]

CSV_PATH = BASE_DIR / "test_video_facial_metrics.csv"
REPORT_PATH = BASE_DIR / "behavior_analysis_report.json"

OUTPUT_DIR = BASE_DIR / "forensics_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    if not REPORT_PATH.exists():
        raise FileNotFoundError(f"Behaviour report not found: {REPORT_PATH}")

    data = pd.read_csv(CSV_PATH)

    with open(REPORT_PATH, "r", encoding="utf-8") as file:
        report = json.load(file)

    return data, report


def plot_ear(data, report):
    events = report["eye_analysis"]["blink_events"]

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(
        data["timestamp_seconds"],
        data["average_ear"],
        linewidth=1.2,
        label="Average EAR",
    )

    ax.axhline(
        y=0.12,
        linestyle="--",
        label="Eye closure threshold (0.12)",
    )

    ax.axhline(
        y=0.18,
        linestyle=":",
        label="Eye reopening threshold (0.18)",
    )

    for event in events:
        if event["event_type"] == "candidate_blink":
            ax.axvspan(
                event["start_time"],
                event["end_time"],
                alpha=0.2,
            )

    ax.set_title("Eye Aspect Ratio (EAR) Over Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Average EAR")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()

    output = OUTPUT_DIR / "ear_timeline.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)

    print(f"EAR graph saved: {output}")


def plot_mar(data, report):
    events = report["mouth_analysis"]["mouth_events"]

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(
        data["timestamp_seconds"],
        data["mouth_aspect_ratio"],
        linewidth=1.2,
        label="Mouth Aspect Ratio (MAR)",
    )

    ax.axhline(
        y=0.60,
        linestyle="--",
        label="High mouth activity threshold (0.60)",
    )

    for event in events:
        ax.axvspan(
            event["start_time"],
            event["end_time"],
            alpha=0.2,
        )

    ax.set_title("Mouth Aspect Ratio (MAR) Over Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("MAR")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()

    output = OUTPUT_DIR / "mar_timeline.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)

    print(f"MAR graph saved: {output}")


def main():
    data, report = load_data()

    plot_ear(data, report)
    plot_mar(data, report)

    print("\nVISUALISATION COMPLETED")


if __name__ == "__main__":
    main()
