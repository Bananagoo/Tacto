"""The printed mat page, checked by detecting what was drawn."""

import cv2
import numpy as np
import pytest

from tacto.mat import Mat
from tacto.vision.kit_render import render_mat
from tacto.vision.markers import find_markers
from tacto.vision.print_geometry import (
    CORNER_MARKER_IDS,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    PrintGeometry,
    mm_to_px,
)

DPI = 150


def grey(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def pixel_at(image: np.ndarray, point_mm: tuple[float, float]) -> int:
    x_px, y_px = (round(mm_to_px(value, dpi=DPI)) for value in point_mm)
    return int(grey(image)[y_px, x_px])


@pytest.fixture(scope="module")
def mat_page(mat) -> np.ndarray:
    return render_mat(mat, dpi=DPI)


def test_the_mat_page_is_a4_landscape_in_colour(mat_page):
    assert mat_page.shape == (
        round(mm_to_px(PAGE_HEIGHT_MM, dpi=DPI)),
        round(mm_to_px(PAGE_WIDTH_MM, dpi=DPI)),
        3,
    )


def test_the_mat_page_has_exactly_the_four_corner_markers_in_place(mat_page, geometry):
    found = {m.id: (m.x_px, m.y_px) for m in find_markers(grey(mat_page))}
    assert sorted(found) == list(CORNER_MARKER_IDS)
    for marker_id, centre_mm in zip(
        CORNER_MARKER_IDS, geometry.corner_marker_centres_mm(), strict=True
    ):
        expected_px = [mm_to_px(value, dpi=DPI) for value in centre_mm]
        assert found[marker_id] == pytest.approx(expected_px, abs=1.5)


def test_every_dot_is_printed_grey_with_paper_between(mat_page, mat, geometry):
    for col in range(mat.cols):
        for row in range(mat.rows):
            x_mm, y_mm = geometry.dot_mm((col, row))
            assert 100 < pixel_at(mat_page, (x_mm, y_mm)) < 200
            assert pixel_at(mat_page, (x_mm + geometry.dot_pitch_mm / 2, y_mm)) == 255


def test_between_the_dots_the_page_is_almost_all_paper(mat_page, mat, geometry):
    """Pieces are told from the paper by colour, so nothing else may be printed there."""
    left_mm, top_mm = geometry.dot_mm((0, 0))
    right_mm, bottom_mm = geometry.dot_mm((mat.cols - 1, mat.rows - 1))
    left, top, right, bottom = (
        round(mm_to_px(v, dpi=DPI)) for v in (left_mm, top_mm, right_mm, bottom_mm)
    )
    area = grey(mat_page)[top:bottom, left:right]
    assert (area < 250).mean() < 0.01


def test_the_dot_spacing_follows_the_mat_file():
    wide = Mat(id="wide", cols=4, rows=3, dot_pitch_mm=40)
    geometry = PrintGeometry.for_mat(wide)
    page = render_mat(wide, dpi=DPI)
    (x0, y0), (x1, _) = geometry.dot_mm((0, 0)), geometry.dot_mm((1, 0))
    assert x1 - x0 == pytest.approx(40)
    assert pixel_at(page, (x1, y0)) < 200
