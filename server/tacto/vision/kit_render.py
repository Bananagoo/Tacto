"""Draw the printable kit from a mat's layout: the mat page and the sheet of tiles.

Pages are plain images so the tests (and the reader's tests) can look at exactly what
gets printed. `kit/make_kit.py` saves them as PDFs.
"""

from __future__ import annotations

import numpy as np

from ..mat.models import Drawable, FixedPart, MatLayout, Segment, Slot, SlotContent
from .page_canvas import Colour, PageCanvas, PointMm, SegmentFrame
from .print_geometry import (
    CORNER_MARKER_IDS,
    CORNER_MARKER_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    TILE_LENGTH_MM,
    TILE_MARKER_IDS,
    TILE_MARKER_MM,
    TILE_MARKER_QUIET_MM,
    TILE_WIDTH_MM,
    PrintGeometry,
    tile_kind,
)
from .symbols import WIRE_WIDTH_MM, draw_symbol

TILES_PER_KIND = 2

# Greys, from the faintest thing on the page to the darkest. The guide for a line the
# learner draws must stay faint: the reader tells pen from guide partly by darkness.
# TODO(vision owner): check these on the venue's printer; a laser prints greys as dots.
_GUIDE_GREY: Colour = (165, 165, 165)
_DOT_GREY: Colour = (150, 150, 150)
_OUTLINE_GREY: Colour = (120, 120, 120)
_LABEL_GREY: Colour = (80, 80, 80)

_DOT_RADIUS_MM = 0.6
_GUIDE_WIDTH_MM = 0.5
_GUIDE_DASH_MM = 0.6  # short dashes far apart: a dotted line that covers a fifth of its length
_GUIDE_GAP_MM = 2.4
_OUTLINE_WIDTH_MM = 0.3
_OUTLINE_DASH_MM = 2.5
_OUTLINE_GAP_MM = 1.5
_LABEL_HEIGHT_MM = 2.2
_GUIDE_LABEL_OFFSET_MM = 6.5  # clear of the strip the reader samples around the line
_PART_LABEL_OFFSET_MM = 11.0  # clear of the widest symbol
_SLOT_LABEL_OFFSET_MM = 3.5

_HEADING_HEIGHT_MM = 2.8
_FOOTER_TEXT_Y_MM = 189.0
_RULER_Y_MM = 196.0
_RULER_MM = 50.0
_RULER_TICK_MM = 2.0

_SHEET_HEADING_Y_MM = 20.0
_SHEET_TILES_TOP_MM = 42.0
_SHEET_GAP_MM = 10.0  # between tiles, so one slip of the scissors spoils nothing
_SHEET_COLUMNS = 4


def render_mat(layout: MatLayout, *, dpi: int = 150) -> np.ndarray:
    """The mat page as a BGR image."""
    geometry = PrintGeometry.for_layout(layout)
    canvas = PageCanvas(PAGE_WIDTH_MM, PAGE_HEIGHT_MM, dpi=dpi)
    for col in range(layout.cols):
        for row in range(layout.rows):
            canvas.circle(geometry.dot_mm((col, row)), _DOT_RADIUS_MM, colour=_DOT_GREY)
    for drawable in layout.drawables:
        _draw_guide(canvas, geometry, drawable)
    for slot in layout.slots:
        _draw_slot(canvas, geometry, slot)
    for wire in layout.wires:
        canvas.line(*_ends_mm(geometry, wire), width_mm=WIRE_WIDTH_MM)
    for part in layout.parts:
        _draw_part(canvas, geometry, part)
    for marker_id, centre in zip(
        CORNER_MARKER_IDS, geometry.corner_marker_centres_mm(), strict=True
    ):
        canvas.marker(marker_id, centre, CORNER_MARKER_MM)
    _draw_scale_check(canvas, f"Tacto mat {layout.id}")
    return canvas.image


def render_tiles(layout: MatLayout, *, dpi: int = 150) -> np.ndarray:
    """The sheet of tiles to cut out: two of each kind the layout's slots accept."""
    kinds = [kind for kind in TILE_MARKER_IDS if any(kind in s.accepts for s in layout.slots)]
    tiles = [
        (kind, marker_id) for kind in kinds for marker_id in TILE_MARKER_IDS[kind][:TILES_PER_KIND]
    ]
    canvas = PageCanvas(PAGE_WIDTH_MM, PAGE_HEIGHT_MM, dpi=dpi)
    canvas.text(
        "Cut along the grey outlines. Keep the white edge around each square pattern:"
        " the camera needs it.",
        (PAGE_WIDTH_MM / 2, _SHEET_HEADING_Y_MM),
        height_mm=_HEADING_HEIGHT_MM,
    )
    row_width_mm = _SHEET_COLUMNS * TILE_LENGTH_MM + (_SHEET_COLUMNS - 1) * _SHEET_GAP_MM
    left_mm = (PAGE_WIDTH_MM - row_width_mm) / 2
    for index, (kind, marker_id) in enumerate(tiles):
        row, column = divmod(index, _SHEET_COLUMNS)
        canvas.paste(
            render_tile(kind, marker_id, dpi=dpi),
            (
                left_mm + column * (TILE_LENGTH_MM + _SHEET_GAP_MM),
                _SHEET_TILES_TOP_MM + row * (TILE_WIDTH_MM + _SHEET_GAP_MM),
            ),
        )
    _draw_scale_check(canvas, f"Tacto tiles for {layout.id}")
    return canvas.image


def render_tile(kind: SlotContent, marker_id: int, *, dpi: int = 150) -> np.ndarray:
    """One tile, lying left to right, with its cut line as the picture's edge."""
    if tile_kind(marker_id) != kind:
        raise ValueError(f"marker {marker_id} does not mean a {kind} tile")
    canvas = PageCanvas(TILE_LENGTH_MM, TILE_WIDTH_MM, dpi=dpi)
    middle_x_mm, middle_y_mm = TILE_LENGTH_MM / 2, TILE_WIDTH_MM / 2
    # The wire's rounded end must stop short of the marker's white edge.
    keep_clear_mm = TILE_MARKER_MM / 2 + TILE_MARKER_QUIET_MM + WIRE_WIDTH_MM / 2
    # The symbol sits in one half so the marker can have the middle, which is the one
    # place a fingertip resting on either end of the tile leaves uncovered.
    draw_symbol(canvas, kind, (0.0, middle_y_mm), (middle_x_mm - keep_clear_mm, middle_y_mm))
    draw_symbol(
        canvas, "wire", (middle_x_mm + keep_clear_mm, middle_y_mm), (TILE_LENGTH_MM, middle_y_mm)
    )
    canvas.marker(marker_id, (middle_x_mm, middle_y_mm), TILE_MARKER_MM)
    canvas.text(
        kind,
        ((middle_x_mm + keep_clear_mm + TILE_LENGTH_MM) / 2, TILE_WIDTH_MM / 4),
        height_mm=_LABEL_HEIGHT_MM,
        colour=_LABEL_GREY,
    )
    _draw_cut_line(canvas)
    return canvas.image


def _ends_mm(geometry: PrintGeometry, segment: Segment) -> tuple[PointMm, PointMm]:
    return geometry.dot_mm(segment.a), geometry.dot_mm(segment.b)


def _draw_guide(canvas: PageCanvas, geometry: PrintGeometry, drawable: Drawable) -> None:
    a, b = _ends_mm(geometry, drawable)
    canvas.dashed_line(
        a,
        b,
        width_mm=_GUIDE_WIDTH_MM,
        dash_mm=_GUIDE_DASH_MM,
        gap_mm=_GUIDE_GAP_MM,
        colour=_GUIDE_GREY,
    )
    _label_beside(canvas, "draw here", a, b, offset_mm=_GUIDE_LABEL_OFFSET_MM)


def _draw_slot(canvas: PageCanvas, geometry: PrintGeometry, slot: Slot) -> None:
    frame = SegmentFrame(*_ends_mm(geometry, slot))
    half_length_mm, half_width_mm = TILE_LENGTH_MM / 2, TILE_WIDTH_MM / 2
    corners = [
        frame.at(-half_length_mm, -half_width_mm),
        frame.at(half_length_mm, -half_width_mm),
        frame.at(half_length_mm, half_width_mm),
        frame.at(-half_length_mm, half_width_mm),
    ]
    for start, end in zip(corners, corners[1:] + corners[:1], strict=True):
        canvas.dashed_line(
            start,
            end,
            width_mm=_OUTLINE_WIDTH_MM,
            dash_mm=_OUTLINE_DASH_MM,
            gap_mm=_OUTLINE_GAP_MM,
            colour=_OUTLINE_GREY,
        )
    # Written inside the outline, so a tile in the slot covers it.
    lines = [" or ".join(slot.accepts) + " tile"]
    if slot.starts != "empty":
        lines.append(f"starts with the {slot.starts}")
    first_mm = -_SLOT_LABEL_OFFSET_MM * (len(lines) - 1) / 2
    for index, line in enumerate(lines):
        across_mm = first_mm + index * _SLOT_LABEL_OFFSET_MM
        # Vertical text reads upward, so its second line goes to the right: the other
        # way round from a frame whose direction of travel is down the page.
        canvas.text(
            line,
            frame.at(0.0, -across_mm if frame.is_vertical else across_mm),
            height_mm=_LABEL_HEIGHT_MM,
            colour=_LABEL_GREY,
            vertical=frame.is_vertical,
        )


def _draw_part(canvas: PageCanvas, geometry: PrintGeometry, part: FixedPart) -> None:
    a, b = _ends_mm(geometry, part)
    draw_symbol(canvas, part.kind, a, b)
    _label_beside(canvas, part.id.replace("_", " "), a, b, offset_mm=_PART_LABEL_OFFSET_MM)


def _label_beside(
    canvas: PageCanvas, text: str, a: PointMm, b: PointMm, *, offset_mm: float
) -> None:
    """Write along a segment, on its side nearer the page edge.

    A circuit is a loop around the middle of the page, so the outer side of any piece
    of it is the side most likely to be free.
    """
    middle_x_mm, middle_y_mm = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    vertical = SegmentFrame(a, b).is_vertical
    if vertical:
        outward = -1 if middle_x_mm <= PAGE_WIDTH_MM / 2 else 1
        centre = (middle_x_mm + outward * offset_mm, middle_y_mm)
    else:
        outward = -1 if middle_y_mm <= PAGE_HEIGHT_MM / 2 else 1
        centre = (middle_x_mm, middle_y_mm + outward * offset_mm)
    canvas.text(text, centre, height_mm=_LABEL_HEIGHT_MM, colour=_LABEL_GREY, vertical=vertical)


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


def _draw_cut_line(canvas: PageCanvas) -> None:
    inset_mm = _OUTLINE_WIDTH_MM / 2
    right_mm, bottom_mm = TILE_LENGTH_MM - inset_mm, TILE_WIDTH_MM - inset_mm
    corners = [
        (inset_mm, inset_mm),
        (right_mm, inset_mm),
        (right_mm, bottom_mm),
        (inset_mm, bottom_mm),
    ]
    canvas.polyline([*corners, corners[0]], width_mm=_OUTLINE_WIDTH_MM, colour=_OUTLINE_GREY)
