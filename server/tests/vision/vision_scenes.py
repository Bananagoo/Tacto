"""Make camera frames without a camera: the printed kit, changed by hand, seen from above.

A scene starts as the rendered mat page. A covering hand is drawn
onto it as a learner would add them, and `photograph` then views the page as a camera
would: at an angle, on a grey desk, a little blurred, dim or noisy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from tacto.mat import Mat
from tacto.vision.kit_render import render_mat
from tacto.vision.print_geometry import (
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    PrintGeometry,
    mm_to_px,
)

PAGE_DPI = 150
FRAME_WIDTH_PX, FRAME_HEIGHT_PX = 1920, 1080
DESK_GREY = (90, 90, 90)
SKIN = (140, 170, 210)
# Card as a camera sees it (BGR): not pure colours. The proposed set in kit/pieces.yaml.
CARD = {
    "wire": (38, 36, 35),
    "battery": (48, 44, 196),
    "bulb": (52, 205, 232),
    "resistor": (186, 96, 34),
    "switch": (72, 152, 46),
}
CARD_WIDTH_MM = 12.0

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

    def __init__(self, mat: Mat) -> None:
        self._geometry = PrintGeometry.for_mat(mat)
        self.page = render_mat(mat, dpi=PAGE_DPI)

    def place(
        self,
        piece: str,
        a: tuple[int, int],
        b: tuple[int, int],
        *,
        width_mm: float = CARD_WIDTH_MM,
        offset_mm: PointMm = (0.0, 0.0),
        turn_deg: float = 0.0,
        colour: tuple[int, int, int] | None = None,
    ) -> Scene:
        """Lay a card strip in the gap between two dots, as carelessly as asked."""
        (ax, ay), (bx, by) = self._geometry.dot_mm(a), self._geometry.dot_mm(b)
        centre = np.array([(ax + bx) / 2 + offset_mm[0], (ay + by) / 2 + offset_mm[1]])
        angle = np.arctan2(by - ay, bx - ax) + np.radians(turn_deg)
        along = np.array([np.cos(angle), np.sin(angle)]) * (self._geometry.dot_pitch_mm / 2)
        across = np.array([-np.sin(angle), np.cos(angle)]) * (width_mm / 2)
        corners = [
            centre - along - across,
            centre + along - across,
            centre + along + across,
            centre - along + across,
        ]
        cv2.fillPoly(
            self.page,
            [np.int32([page_px((float(x), float(y))) for x, y in corners])],
            colour or CARD[piece],
            cv2.LINE_AA,
        )
        return self

    def cover(self, centre_mm: PointMm, radius_mm: float) -> Scene:
        """A hand over part of the page."""
        radius_px = round(mm_to_px(radius_mm, dpi=PAGE_DPI))
        cv2.circle(self.page, page_px(centre_mm), radius_px, SKIN, cv2.FILLED)
        return self

    def cover_corner(self, corner: int) -> Scene:
        return self.cover(self._geometry.corner_marker_centres_mm()[corner], 18.0)

    def photograph(self, view: View = STRAIGHT, *, seed: int = 0) -> np.ndarray:
        return photograph(self.page, view, seed=seed)
