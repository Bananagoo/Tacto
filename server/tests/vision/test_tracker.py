"""Holding the mat's position while a hand covers a corner marker."""

import math

import numpy as np
from vision_scenes import STRAIGHT, TILTED, Scene, frame_position

from tacto.vision.tracker import BLIND_HOLD_S, MatTracker


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def worst_dot_error_mm(flattened, view, mat, geometry) -> float:
    def to_page(point_px):
        x, y, w = flattened.frame_to_page @ np.array([point_px[0], point_px[1], 1.0])
        return float(x / w), float(y / w)

    return max(
        math.dist(to_page(frame_position(view, geometry.dot_mm((c, r)))), geometry.dot_mm((c, r)))
        for c in range(mat.cols)
        for r in range(mat.rows)
    )


def test_a_mat_never_seen_whole_is_not_found(mat, geometry):
    tracker = MatTracker(geometry)
    assert tracker.see(Scene(mat).cover_corner(0).photograph()) is None
    assert tracker.held is False


def test_four_corners_give_a_fresh_position(mat, geometry):
    tracker = MatTracker(geometry)
    flattened = tracker.see(Scene(mat).photograph(TILTED))
    assert flattened is not None and tracker.held is False
    assert worst_dot_error_mm(flattened, TILTED, mat, geometry) < 1.5


def test_a_covered_corner_keeps_the_last_position_and_still_shows_the_new_frame(mat, geometry):
    tracker = MatTracker(geometry)
    tracker.see(Scene(mat).photograph(TILTED))
    covered = Scene(mat).cover_corner(2).place("battery", (3, 2), (4, 2))
    flattened = tracker.see(covered.photograph(TILTED))
    assert flattened is not None and tracker.held is True
    assert worst_dot_error_mm(flattened, TILTED, mat, geometry) < 1.5
    # The piece laid down while the corner was covered is in the flattened picture.
    x_mm, y_mm = np.mean([geometry.dot_mm((3, 2)), geometry.dot_mm((4, 2))], axis=0)
    px_per_mm = flattened.image.shape[1] / 297.0
    blue, green, red = flattened.image[round(y_mm * px_per_mm), round(x_mm * px_per_mm)]
    assert red > 150 and blue < 90 and green < 90


def test_it_holds_for_as_long_as_the_visible_corners_agree(mat, geometry):
    clock = Clock()
    tracker = MatTracker(geometry, clock=clock)
    tracker.see(Scene(mat).photograph())
    frame = Scene(mat).cover_corner(0).cover_corner(1).photograph()
    for _ in range(5):
        clock.now += 10.0
        assert tracker.see(frame) is not None and tracker.held is True


def test_a_mat_that_moved_while_a_corner_was_covered_is_lost(mat, geometry):
    tracker = MatTracker(geometry)
    tracker.see(Scene(mat).photograph(STRAIGHT))
    assert tracker.see(Scene(mat).cover_corner(3).photograph(TILTED)) is None
    assert tracker.held is False
    # And it stays lost until all four corners are seen again.
    assert tracker.see(Scene(mat).cover_corner(3).photograph(STRAIGHT)) is None
    assert tracker.see(Scene(mat).photograph(STRAIGHT)) is not None


def test_with_no_corner_in_sight_it_holds_only_briefly(mat, geometry):
    clock = Clock()
    tracker = MatTracker(geometry, clock=clock)
    tracker.see(Scene(mat).photograph())
    blind = Scene(mat)
    for corner in range(4):
        blind.cover_corner(corner)
    frame = blind.photograph()
    clock.now += BLIND_HOLD_S * 0.5
    assert tracker.see(frame) is not None and tracker.held is True
    clock.now += BLIND_HOLD_S
    assert tracker.see(frame) is None


def test_a_frame_that_is_not_a_picture_is_not_an_error(mat, geometry):
    tracker = MatTracker(geometry)
    assert tracker.see(np.zeros((0, 0, 3), dtype=np.uint8)) is None
