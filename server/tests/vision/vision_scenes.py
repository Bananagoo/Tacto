"""Make camera frames without a camera: the printed kit, changed by hand, seen from above.

A scene starts as the rendered mat page. Pen lines, tiles and a covering hand are drawn
onto it as a learner would add them, and `photograph` then views the page as a camera
would: at an angle, on a grey desk, a little blurred, dim or noisy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from tacto.mat.models import MatLayout, Segment, SlotContent
from tacto.vision.kit_render import render_mat, render_tile
from tacto.vision.print_geometry import (
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    TILE_MARKER_IDS,
    PrintGeometry,
    mm_to_px,
)

PAGE_DPI = 150
FRAME_WIDTH_PX, FRAME_HEIGHT_PX = 1920, 1080
DESK_GREY = (90, 90, 90)
PEN_BLUE = (120, 40, 20)  # BGR: a dark blue ballpoint
PEN_WIDTH_MM = 0.7
SKIN = (140, 170, 210)

PointMm = tuple[float, float]
PointPx = tuple[float, float]


@dataclass(frozen=True)
class View:
    """Where the page's corners land in the frame (clockwise from its top-left), and how
    the picture is degraded."""

    corners_px: tuple[PointPx, PointPx, PointPx, PointPx]
    blur_sigma_px: float = 0.0
    brightness: float = 1.0
    noise_sigma: float = 0.0


# The page filling most of a 1080p frame, slightly turned as a hand-placed sheet is.
STRAIGHT = View(((215, 22), (1712, 6), (1720, 1066), (207, 1074)))
# A camera on a low stand looking across the desk: the far edge is much shorter.
TILTED = View(((470, 110), (1450, 130), (1810, 1010), (110, 980)))
# The same sheet turned half a turn in front of the camera.
UPSIDE_DOWN = View(STRAIGHT.corners_px[2:] + STRAIGHT.corners_px[:2])
BLURRED = replace(STRAIGHT, blur_sigma_px=2.0)
DIM = replace(STRAIGHT, brightness=0.7)
NOISY = replace(STRAIGHT, noise_sigma=6.0)
# Everything at once.
HARSH = replace(TILTED, blur_sigma_px=1.5, brightness=0.7, noise_sigma=4.0)

VIEWS = {
    "straight": STRAIGHT,
    "tilted": TILTED,
    "upside_down": UPSIDE_DOWN,
    "blurred": BLURRED,
    "dim": DIM,
    "noisy": NOISY,
    "harsh": HARSH,
}


def page_px(point_mm: PointMm) -> tuple[int, int]:
    return round(mm_to_px(point_mm[0], dpi=PAGE_DPI)), round(mm_to_px(point_mm[1], dpi=PAGE_DPI))


def page_to_frame(view: View) -> np.ndarray:
    """The homography from page millimetres to frame pixels: the test's ground truth."""
    page_corners_mm = [
        (0, 0),
        (PAGE_WIDTH_MM, 0),
        (PAGE_WIDTH_MM, PAGE_HEIGHT_MM),
        (0, PAGE_HEIGHT_MM),
    ]
    return cv2.getPerspectiveTransform(np.float32(page_corners_mm), np.float32(view.corners_px))


def frame_position(view: View, point_mm: PointMm) -> PointPx:
    x, y, w = page_to_frame(view) @ np.array([point_mm[0], point_mm[1], 1.0])
    return float(x / w), float(y / w)


def photograph(page: np.ndarray, view: View, *, seed: int = 0) -> np.ndarray:
    """A BGR camera frame showing the page as `view` describes."""
    mm_per_page_px = np.diag([25.4 / PAGE_DPI, 25.4 / PAGE_DPI, 1.0])
    frame = cv2.warpPerspective(
        page,
        page_to_frame(view) @ mm_per_page_px,
        (FRAME_WIDTH_PX, FRAME_HEIGHT_PX),
        flags=cv2.INTER_AREA,
        borderValue=DESK_GREY,
    )
    if view.blur_sigma_px > 0:
        frame = cv2.GaussianBlur(frame, (0, 0), view.blur_sigma_px)
    shaded = frame.astype(np.float32) * view.brightness
    if view.noise_sigma > 0:
        shaded += np.random.default_rng(seed).normal(0.0, view.noise_sigma, frame.shape)
    return np.clip(shaded, 0, 255).astype(np.uint8)


class Scene:
    """The mat page with the learner's changes on it."""

    def __init__(self, layout: MatLayout) -> None:
        self._layout = layout
        self._geometry = PrintGeometry.for_layout(layout)
        self.page = render_mat(layout, dpi=PAGE_DPI)

    def draw_line(
        self,
        drawable_id: str,
        *,
        fraction: float = 1.0,
        colour: tuple[int, int, int] = PEN_BLUE,
        width_mm: float = PEN_WIDTH_MM,
        aside_mm: float = 0.0,
    ) -> Scene:
        """A pen line from the drawable's first dot, `fraction` of the way to its second,
        `aside_mm` off the guide as an unsteady hand draws it."""
        (ax, ay), (bx, by) = self._ends_mm(self._find(self._layout.drawables, drawable_id))
        length_mm = float(np.hypot(bx - ax, by - ay))
        shift_x, shift_y = -(by - ay) / length_mm * aside_mm, (bx - ax) / length_mm * aside_mm
        start = (ax + shift_x, ay + shift_y)
        end = (ax + (bx - ax) * fraction + shift_x, ay + (by - ay) * fraction + shift_y)
        thickness_px = max(1, round(mm_to_px(width_mm, dpi=PAGE_DPI)))
        cv2.line(self.page, page_px(start), page_px(end), colour, thickness_px, cv2.LINE_AA)
        return self

    def place_tile(
        self,
        slot_id: str,
        kind: SlotContent,
        *,
        marker_id: int | None = None,
        offset_mm: PointMm = (0.0, 0.0),
    ) -> Scene:
        """Lay a cut-out tile on a slot, `offset_mm` away from sitting exactly on it."""
        tile = render_tile(kind, marker_id or TILE_MARKER_IDS[kind][0], dpi=PAGE_DPI)
        (ax, ay), (bx, by) = self._ends_mm(self._find(self._layout.slots, slot_id))
        if ax == bx:
            tile = np.rot90(tile)
        centre_x, centre_y = page_px(((ax + bx) / 2 + offset_mm[0], (ay + by) / 2 + offset_mm[1]))
        height_px, width_px = tile.shape[:2]
        top, left = centre_y - height_px // 2, centre_x - width_px // 2
        self.page[top : top + height_px, left : left + width_px] = tile
        return self

    def place_starting_tiles(self) -> Scene:
        for slot in self._layout.slots:
            if slot.starts != "empty":
                self.place_tile(slot.id, slot.starts)
        return self

    def cover(self, centre_mm: PointMm, radius_mm: float) -> Scene:
        """A hand over part of the page."""
        radius_px = round(mm_to_px(radius_mm, dpi=PAGE_DPI))
        cv2.circle(self.page, page_px(centre_mm), radius_px, SKIN, cv2.FILLED)
        return self

    def cover_slot(self, slot_id: str) -> Scene:
        (ax, ay), (bx, by) = self._ends_mm(self._find(self._layout.slots, slot_id))
        return self.cover(((ax + bx) / 2, (ay + by) / 2), 20.0)

    def cover_corner(self, corner: int) -> Scene:
        return self.cover(self._geometry.corner_marker_centres_mm()[corner], 18.0)

    def photograph(self, view: View = STRAIGHT, *, seed: int = 0) -> np.ndarray:
        return photograph(self.page, view, seed=seed)

    def _ends_mm(self, segment: Segment) -> tuple[PointMm, PointMm]:
        return self._geometry.dot_mm(segment.a), self._geometry.dot_mm(segment.b)

    @staticmethod
    def _find(items: list, wanted_id: str):
        return next(item for item in items if item.id == wanted_id)
