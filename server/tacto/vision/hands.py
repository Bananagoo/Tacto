"""Hand tracking with MediaPipe Hand Landmarker, on our own camera frames.

Gives every point of each hand in pixels. It reports position only: it cannot
tell a finger resting on the paper from one hovering just above it.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MODEL_PATH = Path(__file__).resolve().parents[2] / "vendor" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
INDEX_TIP = 8  # MediaPipe hand landmark number for the index fingertip
# How MediaPipe's 21 hand points join up: wrist 0, thumb 1-4, index 5-8, middle 9-12,
# ring 13-16, little 17-20.
HAND_BONES = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)  # fmt: skip


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

    def hands(self, frame: np.ndarray, t_ms: int) -> list[dict]:
        """Every hand in the frame: [{handedness, points}], 21 [x, y] pixel points each."""
        # Video mode rejects a timestamp that does not increase.
        t_ms = max(t_ms, self._last_ms + 1)
        self._last_ms = t_ms
        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )
        result = self._landmarker.detect_for_video(image, t_ms)
        height, width = frame.shape[:2]
        return [
            {
                "handedness": handedness[0].category_name,
                "points": [[round(p.x * width), round(p.y * height)] for p in landmarks],
            }
            for landmarks, handedness in zip(result.hand_landmarks, result.handedness, strict=False)
        ]

    def close(self) -> None:
        self._landmarker.close()
