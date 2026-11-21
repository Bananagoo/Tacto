"""Where the mat sits on the printed page.

The kit renderer draws from this and the camera reader measures against it, so the
paper and the software cannot disagree about where a dot, a marker or a tile is.
Everything is in millimetres from the page's top-left corner, x to the right, y down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..contract import Dot
from ..mat.models import MatLayout, SlotContent

MM_PER_INCH = 25.4

# A4, landscape.
PAGE_WIDTH_MM = 297.0
PAGE_HEIGHT_MM = 210.0

# Corner markers fix the page's position and which way up it is.
CORNER_MARKER_IDS = (0, 1, 2, 3)  # top-left, top-right, bottom-right, bottom-left
CORNER_MARKER_MM = 20.0
# Office printers leave about 5 mm at each edge unprinted; stay clear of that.
CORNER_MARKER_INSET_MM = 8.0
# A marker is only found with white paper around it, so nothing is printed this close
# to one. One marker cell is 20 / 6 = 3.3 mm; this leaves a little more.
CORNER_QUIET_MM = 5.0

# TODO(vision owner): pitch and tile sizes were chosen on screen. Check on the printed
# kit that a fingertip fits between two rails and that a cut tile is easy to pick up.
MAX_DOT_PITCH_MM = 30.0  # a small grid must not grow tiles too long to handle
TILE_SPAN_DOTS = 2  # every slot joins two dots this far apart
TILE_WIDTH_MM = 24.0
TILE_MARKER_MM = 14.0
TILE_MARKER_QUIET_MM = 2.5  # one marker cell is 14 / 6 = 2.3 mm

# Five ids per kind, so a kit can hold several tiles of a kind and still tell them apart.
TILE_MARKER_IDS: dict[SlotContent, tuple[int, ...]] = {
    "bulb": (10, 11, 12, 13, 14),
    "wire": (20, 21, 22, 23, 24),
    "resistor": (30, 31, 32, 33, 34),
    "switch": (40, 41, 42, 43, 44),
}
_KIND_OF_MARKER: dict[int, SlotContent] = {
    marker_id: kind for kind, ids in TILE_MARKER_IDS.items() for marker_id in ids
}


def tile_kind(marker_id: int) -> SlotContent | None:
    """The kind of tile that carries this marker, or None for any other marker."""
    return _KIND_OF_MARKER.get(marker_id)


def mm_to_px(length_mm: float, *, dpi: float) -> float:
    return length_mm / MM_PER_INCH * dpi


@dataclass(frozen=True)
class PrintGeometry:
    """The dot grid's place on the page: its pitch and where its first dot is."""

    pitch_mm: float
    first_dot_x_mm: float
    first_dot_y_mm: float

    @classmethod
    def for_layout(cls, layout: MatLayout) -> PrintGeometry:
        """The largest whole-millimetre grid that fits between the corner markers, centred.

        A whole number of millimetres, so a ruler can check the print.
        """
        marker_centre_mm = CORNER_MARKER_INSET_MM + CORNER_MARKER_MM / 2
        clearance_mm = marker_centre_mm + CORNER_MARKER_MM / 2 + CORNER_QUIET_MM
        room_x_mm = PAGE_WIDTH_MM - 2 * clearance_mm
        room_y_mm = PAGE_HEIGHT_MM - 2 * clearance_mm
        fits_mm = math.floor(min(room_x_mm / (layout.cols - 1), room_y_mm / (layout.rows - 1)))
        pitch_mm = min(MAX_DOT_PITCH_MM, float(fits_mm))
        return cls(
            pitch_mm=pitch_mm,
            first_dot_x_mm=(PAGE_WIDTH_MM - (layout.cols - 1) * pitch_mm) / 2,
            first_dot_y_mm=(PAGE_HEIGHT_MM - (layout.rows - 1) * pitch_mm) / 2,
        )

    @property
    def tile_length_mm(self) -> float:
        return TILE_SPAN_DOTS * self.pitch_mm

    def dot_mm(self, dot: Dot) -> tuple[float, float]:
        col, row = dot
        return (
            self.first_dot_x_mm + col * self.pitch_mm,
            self.first_dot_y_mm + row * self.pitch_mm,
        )

    def corner_marker_centres_mm(self) -> list[tuple[float, float]]:
        """Centres of the four corner markers, in CORNER_MARKER_IDS order."""
        near_mm = CORNER_MARKER_INSET_MM + CORNER_MARKER_MM / 2
        right_mm = PAGE_WIDTH_MM - near_mm
        bottom_mm = PAGE_HEIGHT_MM - near_mm
        return [
            (near_mm, near_mm),
            (right_mm, near_mm),
            (right_mm, bottom_mm),
            (near_mm, bottom_mm),
        ]
