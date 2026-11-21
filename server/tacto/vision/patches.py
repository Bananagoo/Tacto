"""Cut the flattened mat into one small picture per segment.

Every piece lies in the gap between two neighbouring dots, so the whole reading
problem is: for each gap, what is lying in it? A patch is the middle of one gap,
always the same size and always lying left to right, whichever way the gap runs,
so one classifier serves every segment.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..contract import Dot, segment_id
from ..mat import Mat
from .flatten import FLAT_DPI, Flattened
from .print_geometry import PrintGeometry, mm_to_px

# Every patch is resized to this, so a classifier sees the same shape for any mat.
PATCH_LENGTH_PX = 48
PATCH_WIDTH_PX = 16
# How much of the gap a patch covers, as fractions of the dot spacing.
# TODO(vision owner): tune on the real kit. Along: the ends are left out, because
# that is where neighbouring pieces overlap and where the printed dots are. Across:
# narrower than the narrowest card strip, so a patch on a piece is all card.
PATCH_ALONG = 0.6
PATCH_ACROSS = 0.25


def segments(mat: Mat) -> list[tuple[Dot, Dot]]:
    """Every gap between neighbouring dots, each as (left or upper dot, other dot).

    Row by row: the gaps running right from each dot, then the gaps running down.
    """
    found: list[tuple[Dot, Dot]] = []
    for row in range(mat.rows):
        for col in range(mat.cols):
            if col + 1 < mat.cols:
                found.append(((col, row), (col + 1, row)))
            if row + 1 < mat.rows:
                found.append(((col, row), (col, row + 1)))
    return found


def cut_patches(flattened: Flattened, mat: Mat, geometry: PrintGeometry) -> dict[str, np.ndarray]:
    """Segment id -> its patch, BGR, PATCH_WIDTH_PX high and PATCH_LENGTH_PX long."""
    px_per_mm = mm_to_px(1.0, dpi=FLAT_DPI)
    half_along_px = PATCH_ALONG * geometry.dot_pitch_mm * px_per_mm / 2
    half_across_px = PATCH_ACROSS * geometry.dot_pitch_mm * px_per_mm / 2
    height_px, width_px = flattened.image.shape[:2]
    patches: dict[str, np.ndarray] = {}
    for a, b in segments(mat):
        (ax_mm, ay_mm), (bx_mm, by_mm) = geometry.dot_mm(a), geometry.dot_mm(b)
        centre_x_px = (ax_mm + bx_mm) / 2 * px_per_mm
        centre_y_px = (ay_mm + by_mm) / 2 * px_per_mm
        runs_down = a[0] == b[0]
        half_x_px, half_y_px = (
            (half_across_px, half_along_px) if runs_down else (half_along_px, half_across_px)
        )
        left, right = round(centre_x_px - half_x_px), round(centre_x_px + half_x_px)
        top, bottom = round(centre_y_px - half_y_px), round(centre_y_px + half_y_px)
        if left < 0 or top < 0 or right > width_px or bottom > height_px:
            continue  # cannot happen for a mat that fits its page; never raise from the reader
        crop = flattened.image[top:bottom, left:right]
        if runs_down:
            crop = cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)
        patches[segment_id(a, b)] = cv2.resize(
            crop, (PATCH_LENGTH_PX, PATCH_WIDTH_PX), interpolation=cv2.INTER_AREA
        )
    return patches
