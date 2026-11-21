"""The ArUco markers on the kit: drawing one, and finding them in a picture."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
# The detector looks for squares; a picture smaller than this cannot hold one, and
# OpenCV's adaptive threshold is not defined on it.
MIN_IMAGE_SIDE_PX = 32

_detector = cv2.aruco.ArucoDetector(DICTIONARY, cv2.aruco.DetectorParameters())


@dataclass(frozen=True)
class FoundMarker:
    id: int
    x_px: float  # the marker's centre
    y_px: float


def marker_image(marker_id: int, side_px: int) -> np.ndarray:
    """A greyscale picture of one marker, black on white, with no border."""
    return cv2.aruco.generateImageMarker(DICTIONARY, marker_id, side_px)


def find_markers(grey: np.ndarray) -> list[FoundMarker]:
    """Every marker in a greyscale picture. The same id can appear more than once."""
    if grey.ndim != 2 or min(grey.shape) < MIN_IMAGE_SIDE_PX:
        return []
    quads, ids, _ = _detector.detectMarkers(grey)
    if ids is None:
        return []
    return [
        FoundMarker(int(marker_id), *_centre(quad.reshape(4, 2)))
        for quad, marker_id in zip(quads, ids.flatten(), strict=True)
    ]


def _centre(quad: np.ndarray) -> tuple[float, float]:
    """Where the diagonals cross.

    Seen at an angle, the average of the four corners is pulled toward the far side of
    the marker; the crossing of the diagonals is still the true centre.
    """
    p0, p1, p2, p3 = quad.astype(float)
    d02, d13 = p2 - p0, p3 - p1
    cross = d02[0] * d13[1] - d02[1] * d13[0]
    if abs(cross) < 1e-9:
        x, y = quad.mean(axis=0)
        return float(x), float(y)
    along = ((p1[0] - p0[0]) * d13[1] - (p1[1] - p0[1]) * d13[0]) / cross
    x, y = p0 + along * d02
    return float(x), float(y)
