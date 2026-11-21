"""The printed pages: the mat and the tiles sheet, checked by detecting what was drawn."""

import cv2
import numpy as np
import pytest

from tacto.mat.models import MatLayout, Slot
from tacto.vision.kit_render import render_mat, render_tile, render_tiles
from tacto.vision.markers import find_markers
from tacto.vision.print_geometry import (
    CORNER_MARKER_IDS,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    TILE_LENGTH_MM,
    TILE_MARKER_IDS,
    TILE_WIDTH_MM,
    mm_to_px,
    tile_kind,
)

DPI = 150


def grey(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def pixel_at(image: np.ndarray, point_mm: tuple[float, float]) -> int:
    x_px, y_px = (round(mm_to_px(value, dpi=DPI)) for value in point_mm)
    return int(grey(image)[y_px, x_px])


def midpoint_mm(geometry, a, b) -> tuple[float, float]:
    (ax, ay), (bx, by) = geometry.dot_mm(a), geometry.dot_mm(b)
    return (ax + bx) / 2, (ay + by) / 2


@pytest.fixture(scope="module")
def mat_page(layout) -> np.ndarray:
    return render_mat(layout, dpi=DPI)


def test_the_mat_page_is_a4_landscape_in_colour(mat_page):
    height_px, width_px, channels = mat_page.shape
    assert width_px == round(mm_to_px(PAGE_WIDTH_MM, dpi=DPI))
    assert height_px == round(mm_to_px(PAGE_HEIGHT_MM, dpi=DPI))
    assert channels == 3


def test_the_mat_page_has_exactly_the_four_corner_markers_in_place(mat_page, geometry):
    found = {marker.id: marker for marker in find_markers(grey(mat_page))}
    assert sorted(found) == list(CORNER_MARKER_IDS)
    for marker_id, (x_mm, y_mm) in zip(
        CORNER_MARKER_IDS, geometry.corner_marker_centres_mm(), strict=True
    ):
        assert found[marker_id].x_px == pytest.approx(mm_to_px(x_mm, dpi=DPI), abs=2)
        assert found[marker_id].y_px == pytest.approx(mm_to_px(y_mm, dpi=DPI), abs=2)


def test_printed_wires_are_solid_black(mat_page, layout, geometry):
    for wire in layout.wires:
        assert pixel_at(mat_page, midpoint_mm(geometry, wire.a, wire.b)) < 40


def test_an_empty_slot_and_an_undrawn_line_are_left_mostly_white(mat_page, layout, geometry):
    # The learner must see that these are gaps, and the reader must not see ink in them.
    for gap in (*layout.slots, *layout.drawables):
        x_mm, y_mm = midpoint_mm(geometry, gap.a, gap.b)
        x_px, y_px = round(mm_to_px(x_mm, dpi=DPI)), round(mm_to_px(y_mm, dpi=DPI))
        patch = grey(mat_page)[y_px - 10 : y_px + 10, x_px - 10 : x_px + 10]
        assert np.mean(patch) > 200


@pytest.mark.parametrize(("kind", "marker_ids"), TILE_MARKER_IDS.items())
def test_a_tile_carries_one_marker_of_its_kind_in_the_middle(kind, marker_ids):
    for marker_id in marker_ids:
        tile = render_tile(kind, marker_id, dpi=DPI)
        height_px, width_px = tile.shape[:2]
        assert width_px == round(mm_to_px(TILE_LENGTH_MM, dpi=DPI))
        assert height_px == round(mm_to_px(TILE_WIDTH_MM, dpi=DPI))
        # A tile is only ever seen lying on paper, so look for it with paper around it.
        on_paper = cv2.copyMakeBorder(tile, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=(255,) * 3)
        (marker,) = find_markers(grey(on_paper))
        assert marker.id == marker_id
        assert tile_kind(marker.id) == kind
        assert marker.x_px - 30 == pytest.approx(width_px / 2, abs=2)
        assert marker.y_px - 30 == pytest.approx(height_px / 2, abs=2)


def test_a_tile_cannot_be_rendered_with_another_kinds_marker():
    with pytest.raises(ValueError, match="marker 20"):
        render_tile("bulb", 20)
    with pytest.raises(ValueError):
        render_tile("empty", 10)


def test_the_tiles_sheet_holds_two_of_each_kind_the_slots_accept(layout):
    sheet = render_tiles(layout, dpi=DPI)
    assert sheet.shape == render_mat(layout, dpi=DPI).shape
    kinds = sorted(tile_kind(marker.id) for marker in find_markers(grey(sheet)))
    assert kinds == ["bulb", "bulb", "wire", "wire"]
    assert len({marker.id for marker in find_markers(grey(sheet))}) == 4


def test_the_tiles_sheet_follows_the_layout():
    layout = MatLayout(
        id="other",
        cols=4,
        rows=3,
        battery_volts=3,
        slots=[
            Slot(id="s1", a=(0, 0), b=(2, 0), accepts=["resistor", "switch"]),
            Slot(id="s2", a=(0, 2), b=(2, 2), accepts=["switch", "bulb", "wire"]),
        ],
    )
    kinds = sorted(tile_kind(m.id) for m in find_markers(grey(render_tiles(layout, dpi=DPI))))
    assert kinds == ["bulb"] * 2 + ["resistor"] * 2 + ["switch"] * 2 + ["wire"] * 2
