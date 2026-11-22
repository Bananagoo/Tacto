"""Cutting the flattened mat into one patch per segment."""

import numpy as np
import pytest
from vision_scenes import CARD, STRAIGHT, TILTED, UPSIDE_DOWN, Scene

from tacto.contract import segment_id
from tacto.mat import Mat
from tacto.vision.flatten import flatten
from tacto.vision.patches import PATCH_LENGTH_PX, PATCH_WIDTH_PX, cut_patches, segments
from tacto.vision.print_geometry import PrintGeometry


def patches_of(scene: Scene, mat, geometry, view=STRAIGHT) -> dict[str, np.ndarray]:
    return cut_patches(flatten(scene.photograph(view), geometry), mat, geometry)


def test_a_grid_has_one_segment_per_gap(mat):
    found = segments(mat)
    # 9 x 6 dots: 8 gaps in each of 6 rows, 5 gaps in each of 9 columns.
    assert len(found) == (mat.cols - 1) * mat.rows + (mat.rows - 1) * mat.cols == 93
    assert len({segment_id(a, b) for a, b in found}) == 93
    for a, b in found:
        assert (b[0] - a[0], b[1] - a[1]) in {(1, 0), (0, 1)}


def test_the_smallest_grid_has_four_segments():
    assert len(segments(Mat(id="tiny", cols=2, rows=2, dot_pitch_mm=40))) == 4


def test_every_segment_gets_a_patch_of_the_same_size(mat, geometry):
    patches = patches_of(Scene(mat), mat, geometry)
    assert set(patches) == {segment_id(a, b) for a, b in segments(mat)}
    assert {patch.shape for patch in patches.values()} == {(PATCH_WIDTH_PX, PATCH_LENGTH_PX, 3)}


def test_an_empty_mat_gives_patches_of_bare_paper(mat, geometry):
    for patch in patches_of(Scene(mat), mat, geometry).values():
        assert patch.min() > 200  # the printed dots are left out of every patch


@pytest.mark.parametrize("view", [STRAIGHT, TILTED, UPSIDE_DOWN])
@pytest.mark.parametrize(
    "a, b", [((2, 1), (3, 1)), ((4, 2), (4, 3)), ((0, 0), (1, 0)), ((8, 4), (8, 5))]
)
def test_a_card_fills_its_own_patch_and_no_other(view, a, b, mat, geometry):
    patches = patches_of(Scene(mat).place("battery", a, b), mat, geometry, view)
    own = patches.pop(segment_id(a, b))
    assert np.abs(own.reshape(-1, 3).mean(axis=0) - CARD["battery"]).max() < 12
    # The segments that meet this one at a dot stay paper, but for a sliver: a 12 mm
    # card is wide enough to clip the corner of a patch running the other way.
    for patch in patches.values():
        assert (patch.min(axis=2) > 200).mean() > 0.93


def test_a_patch_lies_left_to_right_whichever_way_its_gap_runs(mat, geometry):
    """A strip half red, half blue along its length reads the same across and down."""
    scene = Scene(mat)
    for a, b in [((2, 1), (3, 1)), ((5, 2), (5, 3))]:
        (ax, ay), (bx, by) = geometry.dot_mm(a), geometry.dot_mm(b)
        middle = ((ax + bx) / 2, (ay + by) / 2)
        scene.place("battery", a, b)
        # Paint the half nearer the second dot blue.
        half = PrintGeometry(middle[0], middle[1], geometry.dot_pitch_mm / 2)
        step = (1, 0) if a[1] == b[1] else (0, 1)
        (hx, hy), (ix, iy) = half.dot_mm((0, 0)), half.dot_mm(step)
        cv_scene = Scene.__new__(Scene)
        cv_scene._geometry = PrintGeometry(hx, hy, geometry.dot_pitch_mm / 2)
        cv_scene.page = scene.page
        cv_scene.place("resistor", (0, 0), step)
        assert (ix, iy) != (hx, hy)
    patches = patches_of(scene, mat, geometry)
    across, down = patches["2,1-3,1"], patches["5,2-5,3"]
    for patch in (across, down):
        first, second = patch[:, :12].reshape(-1, 3).mean(0), patch[:, -12:].reshape(-1, 3).mean(0)
        assert np.abs(first - CARD["battery"]).max() < 15
        assert np.abs(second - CARD["resistor"]).max() < 15


def test_patch_size_does_not_depend_on_the_dot_spacing():
    wide = Mat(id="wide", cols=5, rows=3, dot_pitch_mm=45)
    geometry = PrintGeometry.for_mat(wide)
    patches = patches_of(Scene(wide).place("bulb", (1, 1), (2, 1)), wide, geometry)
    assert patches["1,1-2,1"].shape == (PATCH_WIDTH_PX, PATCH_LENGTH_PX, 3)
    assert np.abs(patches["1,1-2,1"].reshape(-1, 3).mean(axis=0) - CARD["bulb"]).max() < 12
