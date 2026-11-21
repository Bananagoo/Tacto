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
from tacto.vision.classify import load_colours
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

# The printed pieces (kit/printed/components-v3.pdf): every one 25 mm long and 9 mm wide
# at its ends, most with a wider middle and a symbol. Colours as the sheet defines them.
PRINTED_RGB = load_colours().colours
PIECE_LENGTH_MM = 25.0
PIECE_WIDTH_MM = 9.0
PRINTED_KINDS = ("wire", "bulb", "resistor", "switch_closed", "switch_open", "battery")
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
# The same pieces as the demo camera saw them on 22 Nov 2026 at gain 0, scaled so the paper
# is white (docs/hardware-log.md). Much closer together than the printed values: blue and
# cyan are 22 degrees of hue apart, magenta and red 26. The hard case for the reader.
AS_THE_CAMERA_SEES_RGB = {
    "wire": (30, 62, 137),
    "bulb": (255, 221, 56),
    "resistor": (213, 32, 93),
    "switch_closed": (27, 106, 63),
    "switch_open": (2, 103, 170),
    "battery_positive": (214, 45, 25),
    "battery_negative": (44, 44, 44),
}

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
    cast: tuple[float, float, float] = (1.0, 1.0, 1.0)  # blue, green, red gains: the light's colour


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
# The demo desk on 21 Nov: white paper read (118, 126, 146) as red, green, blue.
BLUE_CAST = replace(TILTED, cast=(1.0, 0.86, 0.81), brightness=0.72, noise_sigma=3.0)
WARM_CAST = replace(STRAIGHT, cast=(0.7, 0.9, 1.0), brightness=0.85, blur_sigma_px=1.0)

VIEWS = {
    "straight": STRAIGHT,
    "tilted": TILTED,
    "upside_down": UPSIDE_DOWN,
    "blurred": BLURRED,
    "dim": DIM,
    "noisy": NOISY,
    "harsh": HARSH,
}
# The views the piece reader is tried under: the above plus coloured light.
READER_VIEWS = {**VIEWS, "blue_cast": BLUE_CAST, "warm_cast": WARM_CAST}


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
    shaded = frame.astype(np.float32) * view.brightness * np.float32(view.cast)
    if view.noise_sigma > 0:
        shaded += np.random.default_rng(seed).normal(0.0, view.noise_sigma, frame.shape)
    return np.clip(shaded, 0, 255).astype(np.uint8)


class Scene:
    """The mat page with the learner's changes on it."""

    def __init__(self, mat: Mat, *, squares: bool = False, rgb: dict | None = None) -> None:
        """`squares` prints the reference colour squares along the top, as the v2 mat has.
        `rgb` gives the pieces and squares other colours than the printed ones."""
        self._geometry = PrintGeometry.for_mat(mat)
        self._rgb = rgb or PRINTED_RGB
        self.page = render_mat(mat, dpi=PAGE_DPI, colours=self._rgb if squares else None)

    def shade(self, top_left_mm: PointMm, bottom_right_mm: PointMm, light: float) -> Scene:
        """A shadow over part of the page: everything in the rectangle keeps `light` of its
        brightness. Call it after laying the pieces it should fall on."""
        (x0, y0), (x1, y1) = page_px(top_left_mm), page_px(bottom_right_mm)
        self.page[y0:y1, x0:x1] = (self.page[y0:y1, x0:x1] * light).astype(np.uint8)
        return self

    def lay(
        self,
        kind: str,
        a: tuple[int, int],
        b: tuple[int, int],
        *,
        positive: str = "a",
        offset_mm: PointMm = (0.0, 0.0),
        turn_deg: float = 0.0,
    ) -> Scene:
        """Lay a printed piece in the gap between two dots. For a battery, `positive` says
        which dot its red half is at."""
        (ax, ay), (bx, by) = self._geometry.dot_mm(a), self._geometry.dot_mm(b)
        centre = np.array([(ax + bx) / 2 + offset_mm[0], (ay + by) / 2 + offset_mm[1]])
        angle = np.arctan2(by - ay, bx - ax) + np.radians(turn_deg)
        along, across = (
            np.array([np.cos(angle), np.sin(angle)]),
            np.array([-np.sin(angle), np.cos(angle)]),
        )

        def at(along_mm: float, across_mm: float) -> tuple[int, int]:
            x, y = centre + along * along_mm + across * across_mm
            return page_px((float(x), float(y)))

        def box(from_mm: float, to_mm: float, width_mm: float, colour) -> None:
            half = width_mm / 2
            corners = [at(from_mm, -half), at(to_mm, -half), at(to_mm, half), at(from_mm, half)]
            cv2.fillPoly(self.page, [np.int32(corners)], colour, cv2.LINE_AA)

        def stroke(points: list[tuple[float, float]], colour, width_mm: float = 0.9) -> None:
            thickness = max(1, round(mm_to_px(width_mm, dpi=PAGE_DPI)))
            line = np.int32([at(x, y) for x, y in points])
            cv2.polylines(self.page, [line], False, colour, thickness, cv2.LINE_AA)

        def bgr(name: str) -> tuple[int, int, int]:
            red, green, blue = self._rgb[name]
            return (blue, green, red)

        end = PIECE_LENGTH_MM / 2
        if kind == "battery":
            red_side = -1 if positive == "a" else 1
            for side, name in ((red_side, "battery_positive"), (-red_side, "battery_negative")):
                box(0.0, side * end, PIECE_WIDTH_MM, bgr(name))
                box(0.0, side * 8.5, 13.0, bgr(name))
            stroke([(red_side * 7.0, -1.5), (red_side * 7.0, 1.5)], BLACK)  # the + sign
            stroke([(red_side * 5.5, 0.0), (red_side * 8.5, 0.0)], BLACK)
            stroke([(-red_side * 5.5, 0.0), (-red_side * 8.5, 0.0)], WHITE)  # the - sign
            return self
        colour = bgr(kind)
        box(-end, end, PIECE_WIDTH_MM, colour)
        if kind == "bulb":
            radius = round(mm_to_px(7.0, dpi=PAGE_DPI))
            cv2.circle(self.page, at(0.0, 0.0), radius, colour, cv2.FILLED, cv2.LINE_AA)
            ring = round(mm_to_px(4.3, dpi=PAGE_DPI))
            cv2.circle(self.page, at(0.0, 0.0), ring, BLACK, 2, cv2.LINE_AA)
            stroke([(-3.0, -3.0), (3.0, 3.0)], BLACK)
            stroke([(-3.0, 3.0), (3.0, -3.0)], BLACK)
        elif kind == "resistor":
            box(-7.5, 7.5, 13.0, colour)
            zigzag = [(-6.0, 0.0), (-4.0, 0.0), (-3.0, -3.0), (-1.0, 3.0), (1.0, -3.0), (3.0, 3.0)]
            stroke([*zigzag, (4.0, 0.0), (6.0, 0.0)], WHITE)
        elif kind in ("switch_closed", "switch_open"):
            box(-8.0, 8.0, 13.0, colour)
            lifted = -3.5 if kind == "switch_open" else 0.0
            stroke([(-4.0, 0.0), (4.0, lifted)], BLACK)
            for x in (-4.0, 4.0):
                cv2.circle(self.page, at(x, 0.0), 3, BLACK, cv2.FILLED, cv2.LINE_AA)
        return self

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
