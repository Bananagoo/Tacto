"""Where the mat sits on the printed page.

The kit renderer draws from this and the camera reader measures against it, so the
paper and the software cannot disagree about where a dot or a marker is.
Everything is in millimetres from the page's top-left corner, x to the right, y down.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contract import Dot
from ..mat import Mat

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


def mm_to_px(length_mm: float, *, dpi: float) -> float:
    return length_mm / MM_PER_INCH * dpi


@dataclass(frozen=True)
class PrintGeometry:
    """The dot grid's place on the page: where its first dot is, and the dot spacing."""

    first_dot_x_mm: float
    first_dot_y_mm: float
    dot_pitch_mm: float

    @classmethod
    def for_mat(cls, mat: Mat) -> PrintGeometry:
        """Centre the mat's grid on the page.

        Raises ValueError for a grid too large to keep clear of the corner markers.
        """
        grid_width_mm = (mat.cols - 1) * mat.dot_pitch_mm
        grid_height_mm = (mat.rows - 1) * mat.dot_pitch_mm
        keep_clear_mm = CORNER_MARKER_INSET_MM + CORNER_MARKER_MM + CORNER_QUIET_MM
        if (
            grid_width_mm > PAGE_WIDTH_MM - 2 * keep_clear_mm
            or grid_height_mm > PAGE_HEIGHT_MM - 2 * keep_clear_mm
        ):
            raise ValueError(
                f"mat {mat.id!r}: a {mat.cols}x{mat.rows} grid at {mat.dot_pitch_mm:g} mm "
                "does not fit on A4 between the corner markers"
            )
        return cls(
            first_dot_x_mm=(PAGE_WIDTH_MM - grid_width_mm) / 2,
            first_dot_y_mm=(PAGE_HEIGHT_MM - grid_height_mm) / 2,
            dot_pitch_mm=mat.dot_pitch_mm,
        )

    def dot_mm(self, dot: Dot) -> tuple[float, float]:
        col, row = dot
        return (
            self.first_dot_x_mm + col * self.dot_pitch_mm,
            self.first_dot_y_mm + row * self.dot_pitch_mm,
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
