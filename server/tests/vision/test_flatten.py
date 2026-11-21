"""Finding the page in a camera frame and squaring it up."""

import math

import cv2
import numpy as np
import pytest
from vision_scenes import STRAIGHT, TILTED, UPSIDE_DOWN, VIEWS, Scene, frame_position

from tacto.vision.flatten import FLAT_DPI, flatten, frame_point_to_mat
from tacto.vision.print_geometry import PAGE_HEIGHT_MM, PAGE_WIDTH_MM, mm_to_px


def to_page_mm(frame_to_page: np.ndarray, point_px: tuple[float, float]) -> tuple[float, float]:
    x, y, w = frame_to_page @ np.array([point_px[0], point_px[1], 1.0])
    return float(x / w), float(y / w)


def all_dots(layout) -> list[tuple[int, int]]:
    return [(col, row) for col in range(layout.cols) for row in range(layout.rows)]


@pytest.mark.parametrize("view_name", VIEWS)
def test_flatten_puts_every_dot_within_a_millimetre_and_a_half(view_name, layout, geometry):
    view = VIEWS[view_name]
    flattened = flatten(Scene(layout).photograph(view), geometry)
    assert flattened is not None
    worst_mm = max(
        math.dist(
            to_page_mm(flattened.frame_to_page, frame_position(view, geometry.dot_mm(dot))),
            geometry.dot_mm(dot),
        )
        for dot in all_dots(layout)
    )
    assert worst_mm < 1.5


@pytest.mark.parametrize("view", [STRAIGHT, TILTED, UPSIDE_DOWN])
def test_the_flattened_image_is_the_page_square_on(view, layout, geometry):
    flattened = flatten(Scene(layout).photograph(view), geometry)
    assert flattened.image.shape == (
        round(mm_to_px(PAGE_HEIGHT_MM, dpi=FLAT_DPI)),
        round(mm_to_px(PAGE_WIDTH_MM, dpi=FLAT_DPI)),
    )
    for wire in layout.wires:
        (ax, ay), (bx, by) = geometry.dot_mm(wire.a), geometry.dot_mm(wire.b)
        x_px = round(mm_to_px((ax + bx) / 2, dpi=FLAT_DPI))
        y_px = round(mm_to_px((ay + by) / 2, dpi=FLAT_DPI))
        assert flattened.image[y_px, x_px] < 100, "a printed wire is where the layout says"


@pytest.mark.parametrize("corner", range(4))
def test_a_hidden_corner_gives_no_result(corner, layout, geometry):
    frame = Scene(layout).cover_corner(corner).photograph()
    assert flatten(frame, geometry) is None


def test_a_corner_marker_seen_twice_gives_no_result(layout, geometry):
    # Two pages in view, or a stray print-out: there is no telling which marker is ours.
    frame = Scene(layout).photograph()
    doubled = np.hstack([frame, frame])
    assert flatten(doubled, geometry) is None


@pytest.mark.parametrize("view", [STRAIGHT, TILTED, UPSIDE_DOWN])
def test_a_frame_point_maps_to_its_mat_position(view, layout, geometry):
    flattened = flatten(Scene(layout).photograph(view), geometry)
    for dot in all_dots(layout):
        x_px, y_px = frame_position(view, geometry.dot_mm(dot))
        x, y = frame_point_to_mat(flattened.frame_to_page, geometry, layout, x_px, y_px)
        assert x == pytest.approx(dot[0] / (layout.cols - 1), abs=0.02)
        assert y == pytest.approx(dot[1] / (layout.rows - 1), abs=0.02)


def test_a_point_beside_the_grid_maps_outside_zero_to_one(layout, geometry):
    flattened = flatten(Scene(layout).photograph(), geometry)
    x_px, y_px = frame_position(STRAIGHT, (5.0, 205.0))  # bottom-left of the page
    x, y = frame_point_to_mat(flattened.frame_to_page, geometry, layout, x_px, y_px)
    assert x < 0 and y > 1


def test_a_greyscale_frame_flattens_like_a_colour_one(layout, geometry):
    frame = Scene(layout).photograph()
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    colour, plain = flatten(frame, geometry), flatten(grey, geometry)
    single_channel = flatten(grey[:, :, np.newaxis], geometry)
    assert np.allclose(colour.frame_to_page, plain.frame_to_page)
    assert np.allclose(colour.frame_to_page, single_channel.frame_to_page)


def test_a_frame_with_an_alpha_channel_flattens(layout, geometry):
    frame = cv2.cvtColor(Scene(layout).photograph(), cv2.COLOR_BGR2BGRA)
    assert flatten(frame, geometry) is not None


@pytest.mark.parametrize(
    "frame",
    [
        np.zeros((1080, 1920, 3), np.uint8),
        np.full((1080, 1920, 3), 255, np.uint8),
        np.zeros((1, 1, 3), np.uint8),
        np.zeros((5, 7), np.uint8),
        np.zeros((0, 0, 3), np.uint8),
        np.zeros((0,), np.uint8),
        np.zeros((480, 640, 2), np.uint8),
        np.zeros((4, 4, 4, 4), np.uint8),
        np.zeros((480, 640, 3), np.float32),
    ],
    ids=["black", "white", "one-pixel", "tiny-grey", "empty", "flat", "two-channel", "4d", "float"],
)
def test_a_frame_with_no_mat_in_it_gives_no_result_and_does_not_raise(frame, geometry):
    assert flatten(frame, geometry) is None
