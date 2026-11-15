
import math


# MediaPipe Face Mesh landmark indices.
# These six points are used to calculate each eye's EAR.

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Mouth landmarks used for MAR calculation.
MOUTH_HORIZONTAL = [61, 291]
MOUTH_VERTICAL_PAIRS = [
    (13, 14),
    (82, 87),
    (312, 317)
]


def euclidean_distance(point_a, point_b):
    """Calculate 2D Euclidean distance between two landmarks."""

    dx = point_a["x"] - point_b["x"]
    dy = point_a["y"] - point_b["y"]

    return math.sqrt(dx ** 2 + dy ** 2)


def calculate_ear(landmarks, eye_indices):
    """
    Calculate Eye Aspect Ratio (EAR).

    A lower EAR generally indicates a more closed eye.
    """

    if len(landmarks) <= max(eye_indices):
        raise ValueError("Insufficient facial landmarks for EAR.")

    p1, p2, p3, p4, p5, p6 = [
        landmarks[index] for index in eye_indices
    ]

    vertical_1 = euclidean_distance(p2, p6)
    vertical_2 = euclidean_distance(p3, p5)
    horizontal = euclidean_distance(p1, p4)

    if horizontal == 0:
        return None

    ear = (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)

    return float(ear)


def calculate_mar(landmarks):
    """
    Calculate Mouth Aspect Ratio (MAR).

    Uses three vertical mouth distances and
    one horizontal mouth width.
    """

    required_indices = (
        MOUTH_HORIZONTAL + [
            index
            for pair in MOUTH_VERTICAL_PAIRS
            for index in pair
        ]
    )

    if len(landmarks) <= max(required_indices):
        raise ValueError("Insufficient facial landmarks for MAR.")

    left_corner = landmarks[MOUTH_HORIZONTAL[0]]
    right_corner = landmarks[MOUTH_HORIZONTAL[1]]

    mouth_width = euclidean_distance(
        left_corner,
        right_corner
    )

    if mouth_width == 0:
        return None

    vertical_distances = []

    for upper_index, lower_index in MOUTH_VERTICAL_PAIRS:
        distance = euclidean_distance(
            landmarks[upper_index],
            landmarks[lower_index]
        )

        vertical_distances.append(distance)

    mar = sum(vertical_distances) / (2.0 * mouth_width)

    return float(mar)


class FacialMetricsAnalyzer:
    """Calculate EAR and MAR from FaceLandmarker output."""

    def analyze_face(self, face_data):

        landmarks = face_data.get("landmarks", [])

        if not landmarks:
            raise ValueError("No facial landmarks provided.")

        left_ear = calculate_ear(
            landmarks,
            LEFT_EYE
        )

        right_ear = calculate_ear(
            landmarks,
            RIGHT_EYE
        )

        valid_ears = [
            value for value in [left_ear, right_ear]
            if value is not None
        ]

        average_ear = (
            sum(valid_ears) / len(valid_ears)
            if valid_ears else None
        )

        mar = calculate_mar(landmarks)

        return {
            "left_eye_ear": left_ear,
            "right_eye_ear": right_ear,
            "average_ear": average_ear,
            "mouth_aspect_ratio": mar
        }
