"""Read the learner's changes off the flattened page.

Only two things on the paper can change: a line drawn where the mat invites one, and
the tile lying in a slot. Everything else is printed, so nothing else is looked at.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from ..mat.models import Drawable, MatLayout, MatReading, Slot, SlotContent
from .flatten import FLAT_DPI, Flattened
from .markers import FoundMarker, find_markers
from .print_geometry import DOT_PITCH_MM, PrintGeometry, mm_to_px, tile_kind

# TODO(vision owner): tune these on frames recorded at the venue.
# A pixel is ink when it is darker than this fraction of the paper beside it. Pen is
# far below it even when blurred; the printed guide, sampled by a camera, is not.
INK_DARKNESS = 0.75
# A line is drawn when ink covers this much of its length: a line stopped a little
# short still counts, a stray stroke or the guide's dashes do not.
DRAWN_FRACTION = 0.5
# Ink shorter than this along the line is not pen: it is one dash of the printed guide
# or a grid dot, both of which are under a millimetre and a half even when blurred.
MIN_INK_RUN_MM = 2.0
# How far to each side of the guide a hand-drawn line may wander.
STRIP_HALF_WIDTH_MM = 3.0
# Printed wires meet the line's two dots; their ink is not the learner's.
STRIP_END_SKIP_MM = 5.0
# Paper is the brightest thing in the strip, but take a little below the maximum so
# one noisy pixel does not set the level.
PAPER_PERCENTILE = 80
# A tile is in a slot when its marker is this close to the slot's middle.
SLOT_REACH_MM = DOT_PITCH_MM / 2

_FLAT_PX_PER_MM = mm_to_px(1.0, dpi=FLAT_DPI)


def read_mat(flattened: Flattened, layout: MatLayout, geometry: PrintGeometry) -> MatReading:
    """Which invited lines are drawn and what lies in each slot. Never raises on a bad image."""
    tiles = [marker for marker in find_markers(flattened.image) if tile_kind(marker.id)]
    return MatReading(
        drawn=frozenset(
            drawable.id
            for drawable in layout.drawables
            if _is_drawn(flattened.image, drawable, geometry)
        ),
        slots={slot.id: _content(slot, tiles, geometry) for slot in layout.slots},
    )


def _is_drawn(image: np.ndarray, drawable: Drawable, geometry: PrintGeometry) -> bool:
    strip = _strip_along(image, geometry.dot_mm(drawable.a), geometry.dot_mm(drawable.b))
    if strip.size == 0:
        return False
    # Judge each step along the line against the paper right beside it, so a shadow
    # or uneven light across the mat does not pass for ink.
    paper = np.percentile(strip, PAPER_PERCENTILE, axis=0)
    has_ink = (strip.min(axis=0) < INK_DARKNESS * paper).astype(np.uint8)
    run_px = max(1, round(MIN_INK_RUN_MM * _FLAT_PX_PER_MM))
    pen = cv2.morphologyEx(has_ink[np.newaxis, :], cv2.MORPH_OPEN, np.ones((1, run_px), np.uint8))
    return float(pen.mean()) >= DRAWN_FRACTION


def _strip_along(
    image: np.ndarray, a_mm: tuple[float, float], b_mm: tuple[float, float]
) -> np.ndarray:
    """The band of the image around the segment a-b, straightened: one column per pixel
    step along the segment, one row per pixel step across it."""
    length_mm = math.dist(a_mm, b_mm)
    along_mm = np.arange(STRIP_END_SKIP_MM, length_mm - STRIP_END_SKIP_MM, 1 / _FLAT_PX_PER_MM)
    across_mm = np.arange(-STRIP_HALF_WIDTH_MM, STRIP_HALF_WIDTH_MM, 1 / _FLAT_PX_PER_MM)
    if along_mm.size == 0:
        return np.empty((0, 0), np.uint8)
    unit_x, unit_y = (b_mm[0] - a_mm[0]) / length_mm, (b_mm[1] - a_mm[1]) / length_mm
    along, across = np.meshgrid(along_mm, across_mm)
    x_px = (a_mm[0] + along * unit_x - across * unit_y) * _FLAT_PX_PER_MM
    y_px = (a_mm[1] + along * unit_y + across * unit_x) * _FLAT_PX_PER_MM
    return cv2.remap(image, x_px.astype(np.float32), y_px.astype(np.float32), cv2.INTER_LINEAR)


def _content(slot: Slot, tiles: list[FoundMarker], geometry: PrintGeometry) -> SlotContent:
    (ax, ay), (bx, by) = geometry.dot_mm(slot.a), geometry.dot_mm(slot.b)
    middle_px = ((ax + bx) / 2 * _FLAT_PX_PER_MM, (ay + by) / 2 * _FLAT_PX_PER_MM)

    def distance_px(tile: FoundMarker) -> float:
        return math.dist(middle_px, (tile.x_px, tile.y_px))

    nearest = min(tiles, key=distance_px, default=None)
    if nearest is None or distance_px(nearest) > SLOT_REACH_MM * _FLAT_PX_PER_MM:
        return "empty"
    kind = tile_kind(nearest.id)
    # A tile the slot does not take is a mistake on the desk, not a part of the circuit.
    return kind if kind in slot.accepts else "empty"
