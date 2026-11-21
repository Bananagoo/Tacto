"""Draw the printable mat: a grid of dots between four corner markers, with a square of
each piece colour along the top edge.

The page is a plain image so the tests (and the reader's tests) can look at exactly
what gets printed. `kit/make_kit.py` saves it as a PDF. The pieces are printed from
their own sheet (kit/printed/) and carry no markers.
"""

from __future__ import annotations

import numpy as np

from ..mat import Mat
from .page_canvas import Colour, PageCanvas
from .print_geometry import (
    CORNER_MARKER_IDS,
    CORNER_MARKER_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    REFERENCE_SQUARE_MM,
    PrintGeometry,
)

# Dots are grey and small so that they never read as a piece, yet show where pieces go.
# TODO(vision owner): check on the venue's printer; a laser prints greys as dots.
_DOT_GREY: Colour = (150, 150, 150)
_DOT_RADIUS_MM = 0.9

_OUTLINE_WIDTH_MM = 0.3
_HEADING_HEIGHT_MM = 2.8
_FOOTER_TEXT_Y_MM = 189.0
_RULER_Y_MM = 196.0
_RULER_MM = 50.0
_RULER_TICK_MM = 2.0


def render_mat(
    mat: Mat, *, dpi: int = 150, colours: dict[str, tuple[int, int, int]] | None = None
) -> np.ndarray:
    """The mat page as a BGR image. `colours` is colour name -> (red, green, blue) for the
    reference squares; without it the mat is printed without them."""
    geometry = PrintGeometry.for_mat(mat)
    canvas = PageCanvas(PAGE_WIDTH_MM, PAGE_HEIGHT_MM, dpi=dpi)
    for name, centre in geometry.reference_square_centres_mm(mat.cols).items():
        if colours and name in colours:
            red, green, blue = colours[name]
            canvas.square(centre, REFERENCE_SQUARE_MM, colour=(blue, green, red))
    for col in range(mat.cols):
        for row in range(mat.rows):
            canvas.circle(geometry.dot_mm((col, row)), _DOT_RADIUS_MM, colour=_DOT_GREY)
    for marker_id, centre in zip(
        CORNER_MARKER_IDS, geometry.corner_marker_centres_mm(), strict=True
    ):
        canvas.marker(marker_id, centre, CORNER_MARKER_MM)
    _draw_scale_check(canvas, f"Tacto mat {mat.id}")
    return canvas.image


def _draw_scale_check(canvas: PageCanvas, title: str) -> None:
    """The footer: what the page is, and a bar to hold a ruler against after printing."""
    canvas.text(
        f"{title}  -  print at 100% (no scaling)  -  the bar below is {_RULER_MM:g} mm long",
        (PAGE_WIDTH_MM / 2, _FOOTER_TEXT_Y_MM),
        height_mm=_HEADING_HEIGHT_MM,
    )
    left_mm = (PAGE_WIDTH_MM - _RULER_MM) / 2
    right_mm = left_mm + _RULER_MM
    canvas.line((left_mm, _RULER_Y_MM), (right_mm, _RULER_Y_MM), width_mm=_OUTLINE_WIDTH_MM)
    for x_mm in (left_mm, right_mm):
        canvas.line(
            (x_mm, _RULER_Y_MM - _RULER_TICK_MM),
            (x_mm, _RULER_Y_MM + _RULER_TICK_MM),
            width_mm=_OUTLINE_WIDTH_MM,
        )
