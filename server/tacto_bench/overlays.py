"""What the camera bench draws on a frame: ArUco markers and the hand points.

For checking the hardware by eye. The lab's own mat reading lives in tacto.vision.
"""

from __future__ import annotations

import cv2
import numpy as np

from tacto.vision.hands import HAND_BONES, INDEX_TIP, HandTracker

# The printed test sheet (scripts/aruco_probe.py) puts these in the corners.
CORNER_IDS = (0, 1, 2, 3)
JPEG_QUALITY = 80

_DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def analyse(
    frame: np.ndarray,
    overlays: set[str],
    tracker: HandTracker | None,
    t_ms: int,
) -> tuple[np.ndarray, dict]:
    """Run the requested checks on a frame. Returns the frame to show and what was found."""
    height, width = frame.shape[:2]
    analysis: dict = {
        "width": width,
        "height": height,
        "brightness": round(float(frame.mean()), 1),
    }
    drawn = frame

    if "aruco" in overlays:
        detector = cv2.aruco.ArucoDetector(_DICTIONARY, cv2.aruco.DetectorParameters())
        corners, ids, _ = detector.detectMarkers(frame)
        found = [] if ids is None else [int(i) for i in ids.flatten()]
        analysis["marker_ids"] = sorted(found)
        analysis["missing_corners"] = sorted(set(CORNER_IDS) - set(found))
        analysis["corners_visible"] = not analysis["missing_corners"]
        if found:
            drawn = drawn.copy()
            cv2.aruco.drawDetectedMarkers(drawn, corners, ids)

    if "hand" in overlays and tracker is not None:
        hands = tracker.hands(frame, t_ms)
        analysis["hands"] = hands
        analysis["fingertips"] = [
            {
                "handedness": hand["handedness"],
                "x": hand["points"][INDEX_TIP][0],
                "y": hand["points"][INDEX_TIP][1],
            }
            for hand in hands
        ]
        if hands:
            if drawn is frame:
                drawn = drawn.copy()
            for hand in hands:
                points = [tuple(point) for point in hand["points"]]
                for start, end in HAND_BONES:
                    cv2.line(drawn, points[start], points[end], (255, 200, 0), 3)
                for number, point in enumerate(points):
                    cv2.circle(drawn, point, 7, (0, 255, 0), -1)
                    cv2.putText(
                        drawn,
                        str(number),
                        (point[0] + 9, point[1] - 9),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2,
                    )
                cv2.circle(drawn, points[INDEX_TIP], 18, (0, 0, 255), 4)

    return drawn, analysis


def encode_jpeg(frame: np.ndarray, width: int) -> bytes:
    """JPEG bytes, scaled down to `width` so the preview stays light."""
    height = frame.shape[0]
    if 0 < width < frame.shape[1]:
        height = round(frame.shape[0] * width / frame.shape[1])
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise ValueError("could not encode frame")
    return encoded.tobytes()
