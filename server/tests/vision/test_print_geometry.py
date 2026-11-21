"""Where the mat lands on the page, and which marker ids mean which tile."""

import pytest

from tacto.mat.models import MatLayout
from tacto.vision.print_geometry import (
    CORNER_MARKER_IDS,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    TILE_MARKER_IDS,
    PrintGeometry,
    mm_to_px,
    tile_kind,
)


def all_dots(layout: MatLayout) -> list[tuple[int, int]]:
    return [(col, row) for col in range(layout.cols) for row in range(layout.rows)]


def test_every_dot_is_on_the_page_and_well_inside_the_corner_markers(layout, geometry):
    centres = geometry.corner_marker_centres_mm()
    left, top = centres[0]
    right, bottom = centres[2]
    for dot in all_dots(layout):
        x_mm, y_mm = geometry.dot_mm(dot)
        assert 0 < x_mm < PAGE_WIDTH_MM and 0 < y_mm < PAGE_HEIGHT_MM
        assert left + 10 <= x_mm <= right - 10
        assert top + 10 <= y_mm <= bottom - 10


def test_corner_markers_are_listed_clockwise_from_the_top_left(geometry):
    (tl_x, tl_y), (tr_x, tr_y), (br_x, br_y), (bl_x, bl_y) = geometry.corner_marker_centres_mm()
    assert len(CORNER_MARKER_IDS) == 4
    assert tl_x == bl_x < tr_x == br_x
    assert tl_y == tr_y < bl_y == br_y
    # The same distance from every page edge, so the mat looks the same either way up.
    assert tl_x == pytest.approx(PAGE_WIDTH_MM - tr_x)
    assert tl_y == pytest.approx(PAGE_HEIGHT_MM - bl_y)


def test_dot_pitch_is_the_same_in_both_directions(geometry):
    x0, y0 = geometry.dot_mm((0, 0))
    x1, y1 = geometry.dot_mm((1, 1))
    assert x1 - x0 == pytest.approx(geometry.pitch_mm)
    assert y1 - y0 == pytest.approx(geometry.pitch_mm)


def test_the_grid_is_centred_on_the_page(layout, geometry):
    first_x, first_y = geometry.dot_mm((0, 0))
    last_x, last_y = geometry.dot_mm((layout.cols - 1, layout.rows - 1))
    assert first_x == pytest.approx(PAGE_WIDTH_MM - last_x)
    assert first_y == pytest.approx(PAGE_HEIGHT_MM - last_y)


def test_a_tile_spans_two_dots(geometry):
    assert geometry.tile_length_mm == pytest.approx(2 * geometry.pitch_mm)


def test_a_small_grid_does_not_get_giant_tiles():
    small = PrintGeometry.for_layout(MatLayout(id="small", cols=3, rows=2, battery_volts=6))
    assert small.pitch_mm <= 30


def test_marker_ids_map_to_tile_kinds():
    assert tile_kind(10) == "bulb"
    assert tile_kind(14) == "bulb"
    assert tile_kind(20) == "wire"
    assert tile_kind(30) == "resistor"
    assert tile_kind(44) == "switch"
    for kind, ids in TILE_MARKER_IDS.items():
        assert all(tile_kind(marker_id) == kind for marker_id in ids)


@pytest.mark.parametrize("marker_id", [*CORNER_MARKER_IDS, 4, 9, 15, 25, 45, 49, -1])
def test_other_marker_ids_are_not_tiles(marker_id):
    assert tile_kind(marker_id) is None


def test_millimetres_to_pixels_follows_the_dpi():
    assert mm_to_px(25.4, dpi=150) == pytest.approx(150)
    assert mm_to_px(50.8, dpi=100) == pytest.approx(200)
