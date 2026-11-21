"""Find the mat's page in a camera frame and square it up.

The four corner markers say where the page is and which way up, so the mat can lie at
any angle, or be turned right round, under the camera.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from ..mat import Mat
from .markers import find_markers
from .print_geometry import (
    CORNER_MARKER_IDS,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    PrintGeometry,
    mm_to_px,
)

# About what a 1080p camera sees of an A4 page that fills its frame: more would only
# invent pixels. A 28 mm dot gap is 110 pixels long at this scale.
FLAT_DPI = 100


@dataclass(frozen=True)
class Flattened:
    image: np.ndarray  # the page, square-on, at FLAT_DPI, in colour (BGR)
    frame_to_page: np.ndarray  # 3x3 homography, frame pixels -> page millimetres


def flatten(frame: np.ndarray, geometry: PrintGeometry) -> Flattened | None:
    """The page as seen from straight above, or None unless all four corners are found.

    Accepts whatever a camera or an image file hands over (colour, greyscale, with or
    without alpha) and answers None, never raises, for a frame it cannot use.
    """
    corners = seen_corners(frame)
    if corners is None or len(corners) != len(CORNER_MARKER_IDS):
        return None
    frame_to_page = fit_frame_to_page(corners, geometry)
    if frame_to_page is None:
        return None
    return warp(frame, frame_to_page)


def seen_corners(frame: np.ndarray) -> dict[int, tuple[float, float]] | None:
    """Corner marker id -> its centre in the frame, for each corner seen exactly once.

    None for a frame that is not a picture. A corner seen twice is left out: a second
    mat or a stray print is in view, and there is no telling which one is ours.
    """
    grey = _as_grey(frame)
    if grey is None:
        return None
    centres: dict[int, tuple[float, float]] = {}
    twice: set[int] = set()
    for marker in find_markers(grey):
        if marker.id not in CORNER_MARKER_IDS:
            continue
        if marker.id in centres:
            twice.add(marker.id)
        centres[marker.id] = (marker.x_px, marker.y_px)
    return {marker_id: centre for marker_id, centre in centres.items() if marker_id not in twice}


def fit_frame_to_page(
    corners: dict[int, tuple[float, float]], geometry: PrintGeometry
) -> np.ndarray | None:
    """The homography from frame pixels to page millimetres, from all four corners."""
    if any(marker_id not in corners for marker_id in CORNER_MARKER_IDS):
        return None
    frame_to_page = cv2.getPerspectiveTransform(
        np.float32([corners[marker_id] for marker_id in CORNER_MARKER_IDS]),
        np.float32(geometry.corner_marker_centres_mm()),
    )
    # Four centres nearly in a line (a false detection) give a transform that cannot be
    # undone; nothing read through it would mean anything.
    if not np.all(np.isfinite(frame_to_page)) or abs(np.linalg.det(frame_to_page)) < 1e-12:
        return None
    return frame_to_page


def warp(frame: np.ndarray, frame_to_page: np.ndarray) -> Flattened | None:
    """The frame squared up through a known homography. None for a frame that is not a picture."""
    grey = _as_grey(frame)
    if grey is None:
        return None
    flat_px_per_mm = mm_to_px(1.0, dpi=FLAT_DPI)
    page_to_flat = np.diag([flat_px_per_mm, flat_px_per_mm, 1.0])
    size_px = (round(PAGE_WIDTH_MM * flat_px_per_mm), round(PAGE_HEIGHT_MM * flat_px_per_mm))
    image = cv2.warpPerspective(
        _as_colour(frame, grey), page_to_flat @ frame_to_page, size_px, flags=cv2.INTER_LINEAR
    )
    return Flattened(image=image, frame_to_page=frame_to_page)


def frame_point_to_mat(
    frame_to_page: np.ndarray,
    geometry: PrintGeometry,
    mat: Mat,
    x_px: float,
    y_px: float,
) -> tuple[float, float]:
    """A point in the camera frame as a mat position.

    Mat position runs 0..1 from the first dot column or row to the last, so a point
    beside the grid falls outside 0..1.
    """
    x, y, w = frame_to_page @ np.array([x_px, y_px, 1.0])
    if abs(w) < 1e-12:
        # On the horizon of the page's plane: as far off the mat as a point can be.
        return math.inf, math.inf
    first_x_mm, first_y_mm = geometry.dot_mm((0, 0))
    return (
        (x / w - first_x_mm) / ((mat.cols - 1) * geometry.dot_pitch_mm),
        (y / w - first_y_mm) / ((mat.rows - 1) * geometry.dot_pitch_mm),
    )


def _as_colour(frame: np.ndarray, grey: np.ndarray) -> np.ndarray:
    """The frame as BGR. `grey` is the same frame as `_as_grey` made it."""
    if frame.ndim == 3 and frame.shape[2] == 3:
        return frame
    if frame.ndim == 3 and frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)


def _as_grey(frame: np.ndarray) -> np.ndarray | None:
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.size == 0:
        return None
    if frame.ndim == 2:
        return frame
    if frame.ndim != 3:
        return None
    channels = frame.shape[2]
    if channels == 1:
        return frame[:, :, 0]
    if channels == 3:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if channels == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    return None
