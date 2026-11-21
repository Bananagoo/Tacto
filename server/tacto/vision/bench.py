"""What the hardware test bench draws on a camera frame: ArUco markers and the fingertip.

This is for checking the hardware by eye, not the mat-reading pipeline.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

# The printed test sheet (scripts/aruco_probe.py) puts these in the corners.
# TODO(vision owner): take the corner ids from the kit geometry module once it exists.
CORNER_IDS = (0, 1, 2, 3)
MODEL_PATH = Path(__file__).resolve().parents[2] / "vendor" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
INDEX_TIP = 8  # MediaPipe hand landmark number for the index fingertip
JPEG_QUALITY = 80

_DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


class HandTrackingUnavailable(RuntimeError):
    pass


class HandTracker:
    """MediaPipe Hand Landmarker in video mode. One per stream; not thread-safe."""

    def __init__(self) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision
        except ImportError as error:
            raise HandTrackingUnavailable("mediapipe is not installed; run make setup") from error
        if not MODEL_PATH.exists():
            raise HandTrackingUnavailable(
                f"hand model missing; run: curl -L -o {MODEL_PATH} {MODEL_URL}"
            )
        self._mp = mp
        self._landmarker = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
            )
        )
        self._last_ms = -1

    def fingertips(self, frame: np.ndarray, t_ms: int) -> list[dict]:
        """Index fingertips in pixels: [{handedness, x, y}]."""
        # Video mode rejects a timestamp that does not increase.
        t_ms = max(t_ms, self._last_ms + 1)
        self._last_ms = t_ms
        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )
        result = self._landmarker.detect_for_video(image, t_ms)
        height, width = frame.shape[:2]
        tips = []
        for landmarks, handedness in zip(result.hand_landmarks, result.handedness, strict=False):
            tip = landmarks[INDEX_TIP]
            tips.append(
                {
                    "handedness": handedness[0].category_name,
                    "x": round(tip.x * width),
                    "y": round(tip.y * height),
                }
            )
        return tips

    def close(self) -> None:
        self._landmarker.close()


def analyse(
    frame: np.ndarray, overlays: set[str], tracker: HandTracker | None, t_ms: int
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
        tips = tracker.fingertips(frame, t_ms)
        analysis["fingertips"] = tips
        if tips:
            if drawn is frame:
                drawn = drawn.copy()
            for tip in tips:
                cv2.circle(drawn, (tip["x"], tip["y"]), 18, (0, 0, 255), 4)

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
