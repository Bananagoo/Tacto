"""A white page to draw on in millimetres, whatever resolution it is rendered at."""

from __future__ import annotations

import math

import cv2
import numpy as np

from .markers import marker_image
from .print_geometry import mm_to_px

PointMm = tuple[float, float]
Colour = tuple[int, int, int]  # blue, green, red: OpenCV's order

BLACK: Colour = (0, 0, 0)
WHITE: Colour = (255, 255, 255)

_FONT = cv2.FONT_HERSHEY_SIMPLEX
# OpenCV draws at whole pixels unless told how many fractional bits a coordinate has.
# Sixteenths of a pixel keep a 150 dpi page true to a tenth of a millimetre.
_SHIFT = 4
_TEXT_STROKE_PER_HEIGHT = 0.11  # a stroke this fraction of the letter height reads well


class SegmentFrame:
    """Positions along and across the line from a to b, measured from its middle."""

    def __init__(self, a: PointMm, b: PointMm) -> None:
        self.length_mm = math.dist(a, b)
        if self.length_mm == 0:
            raise ValueError("a segment needs two different ends")
        self._middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        self._along = ((b[0] - a[0]) / self.length_mm, (b[1] - a[1]) / self.length_mm)

    @property
    def is_vertical(self) -> bool:
        return abs(self._along[0]) < 1e-9

    def at(self, along_mm: float, across_mm: float = 0.0) -> PointMm:
        """Across is to the right of the direction of travel, turned a quarter clockwise."""
        along_x, along_y = self._along
        return (
            self._middle[0] + along_mm * along_x - across_mm * along_y,
            self._middle[1] + along_mm * along_y + across_mm * along_x,
        )


class PageCanvas:
    def __init__(self, width_mm: float, height_mm: float, *, dpi: int) -> None:
        self._dpi = dpi
        self.image = np.full(
            (round(self._px(height_mm)), round(self._px(width_mm)), 3), 255, np.uint8
        )

    def line(self, a: PointMm, b: PointMm, *, width_mm: float, colour: Colour = BLACK) -> None:
        cv2.line(
            self.image,
            self._point(a),
            self._point(b),
            colour,
            self._stroke(width_mm),
            cv2.LINE_AA,
            _SHIFT,
        )

    def dashed_line(
        self,
        a: PointMm,
        b: PointMm,
        *,
        width_mm: float,
        dash_mm: float,
        gap_mm: float,
        colour: Colour = BLACK,
    ) -> None:
        length_mm = math.dist(a, b)
        if length_mm == 0:
            return
        ux, uy = (b[0] - a[0]) / length_mm, (b[1] - a[1]) / length_mm
        start_mm = 0.0
        while start_mm < length_mm:
            end_mm = min(start_mm + dash_mm, length_mm)
            self.line(
                (a[0] + ux * start_mm, a[1] + uy * start_mm),
                (a[0] + ux * end_mm, a[1] + uy * end_mm),
                width_mm=width_mm,
                colour=colour,
            )
            start_mm += dash_mm + gap_mm

    def polyline(self, points: list[PointMm], *, width_mm: float, colour: Colour = BLACK) -> None:
        for a, b in zip(points, points[1:], strict=False):
            self.line(a, b, width_mm=width_mm, colour=colour)

    def square(self, centre: PointMm, side_mm: float, *, colour: Colour) -> None:
        """A filled square."""
        half = side_mm / 2
        cv2.rectangle(
            self.image,
            self._point((centre[0] - half, centre[1] - half)),
            self._point((centre[0] + half, centre[1] + half)),
            colour,
            cv2.FILLED,
            cv2.LINE_AA,
            _SHIFT,
        )

    def circle(
        self,
        centre: PointMm,
        radius_mm: float,
        *,
        width_mm: float | None = None,
        colour: Colour = BLACK,
    ) -> None:
        """An outline `width_mm` wide, or a filled disc when no width is given."""
        thickness = cv2.FILLED if width_mm is None else self._stroke(width_mm)
        radius = round(self._px(radius_mm) * (1 << _SHIFT))
        cv2.circle(self.image, self._point(centre), radius, colour, thickness, cv2.LINE_AA, _SHIFT)

    def text(
        self,
        text: str,
        centre: PointMm,
        *,
        height_mm: float,
        colour: Colour = BLACK,
        vertical: bool = False,
    ) -> None:
        """Text centred on a point. Vertical text reads from the bottom of the page up."""
        height_px = max(4, round(self._px(height_mm)))
        stroke_px = max(1, round(height_px * _TEXT_STROKE_PER_HEIGHT))
        scale = cv2.getFontScaleFromHeight(_FONT, height_px, stroke_px)
        (width_px, _), baseline_px = cv2.getTextSize(text, _FONT, scale, stroke_px)
        pad_px = stroke_px + 1
        label = np.full(
            (height_px + baseline_px + 2 * pad_px, width_px + 2 * pad_px, 3), 255, np.uint8
        )
        origin = (pad_px, pad_px + height_px)
        cv2.putText(label, text, origin, _FONT, scale, colour, stroke_px, cv2.LINE_AA)
        if vertical:
            label = np.rot90(label)
        self._darken(label, centre)

    def marker(self, marker_id: int, centre: PointMm, side_mm: float) -> None:
        side_px = round(self._px(side_mm))
        left_px = round(self._px(centre[0]) - side_px / 2)
        top_px = round(self._px(centre[1]) - side_px / 2)
        self.image[top_px : top_px + side_px, left_px : left_px + side_px] = marker_image(
            marker_id, side_px
        )[:, :, np.newaxis]

    def paste(self, picture: np.ndarray, top_left: PointMm) -> None:
        left_px, top_px = round(self._px(top_left[0])), round(self._px(top_left[1]))
        height_px, width_px = picture.shape[:2]
        self.image[top_px : top_px + height_px, left_px : left_px + width_px] = picture

    def _darken(self, label: np.ndarray, centre: PointMm) -> None:
        """Lay a black-on-white label over the page without wiping what is under its white."""
        height_px, width_px = label.shape[:2]
        left_px = round(self._px(centre[0]) - width_px / 2)
        top_px = round(self._px(centre[1]) - height_px / 2)
        page_height_px, page_width_px = self.image.shape[:2]
        x0, y0 = max(left_px, 0), max(top_px, 0)
        x1, y1 = min(left_px + width_px, page_width_px), min(top_px + height_px, page_height_px)
        if x0 >= x1 or y0 >= y1:
            return
        visible = label[y0 - top_px : y1 - top_px, x0 - left_px : x1 - left_px]
        self.image[y0:y1, x0:x1] = np.minimum(self.image[y0:y1, x0:x1], visible)

    def _px(self, length_mm: float) -> float:
        return mm_to_px(length_mm, dpi=self._dpi)

    def _point(self, point: PointMm) -> tuple[int, int]:
        scale = 1 << _SHIFT
        return round(self._px(point[0]) * scale), round(self._px(point[1]) * scale)

    def _stroke(self, width_mm: float) -> int:
        return max(1, round(self._px(width_mm)))
