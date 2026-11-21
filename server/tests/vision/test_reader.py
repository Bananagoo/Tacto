"""Reading the learner's changes off the flattened page: drawn lines and tiles in slots."""

import numpy as np
import pytest
from vision_scenes import STRAIGHT, VIEWS, Scene, View

from tacto.mat.compose import compose
from tacto.mat.models import MatLayout, MatReading
from tacto.vision.flatten import Flattened, flatten
from tacto.vision.print_geometry import DOT_PITCH_MM, PrintGeometry
from tacto.vision.reader import read_mat

# The degradations the plan names, alone and together, and the mat turned right round.
ALL_VIEWS = list(VIEWS)


def read(scene: Scene, layout: MatLayout, view: View = STRAIGHT) -> MatReading:
    geometry = PrintGeometry.for_layout(layout)
    flattened = flatten(scene.photograph(view), geometry)
    assert flattened is not None, "the scene's corner markers should be visible"
    return read_mat(flattened, layout, geometry)


@pytest.mark.parametrize("view_name", ALL_VIEWS)
def test_the_kit_as_shipped_reads_as_the_initial_reading(view_name, layout):
    scene = Scene(layout).place_starting_tiles()
    assert read(scene, layout, VIEWS[view_name]) == layout.initial_reading()


@pytest.mark.parametrize("view_name", ALL_VIEWS)
def test_the_bare_mat_has_nothing_drawn_and_every_slot_empty(view_name, layout):
    # The dotted guides are printed where lines go; they are not lines.
    reading = read(Scene(layout), layout, VIEWS[view_name])
    assert reading.drawn == frozenset()
    assert reading.slots == {"tile": "empty", "side": "empty"}


@pytest.mark.parametrize("view_name", ALL_VIEWS)
@pytest.mark.parametrize("drawn", [("gap",), ("shortcut",), ("gap", "shortcut")])
def test_pen_lines_are_read_on_the_drawables_they_cover(view_name, drawn, layout):
    scene = Scene(layout).place_starting_tiles()
    for drawable_id in drawn:
        scene.draw_line(drawable_id)
    assert read(scene, layout, VIEWS[view_name]).drawn == frozenset(drawn)


@pytest.mark.parametrize("view_name", ALL_VIEWS)
@pytest.mark.parametrize(
    ("slot_id", "content"),
    [("tile", "wire"), ("tile", "bulb"), ("tile", "empty"), ("side", "bulb"), ("side", "wire")],
)
def test_each_slot_reads_each_tile_it_accepts(view_name, slot_id, content, layout):
    scene = Scene(layout)
    if content != "empty":
        scene.place_tile(slot_id, content)
    reading = read(scene, layout, VIEWS[view_name])
    other_id = "side" if slot_id == "tile" else "tile"
    assert reading.slots == {slot_id: content, other_id: "empty"}


@pytest.mark.parametrize("view_name", ALL_VIEWS)
def test_the_whole_lesson_mat_reads_at_once(view_name, layout):
    scene = Scene(layout).place_tile("tile", "bulb").place_tile("side", "wire", marker_id=22)
    scene.draw_line("gap").draw_line("shortcut")
    assert read(scene, layout, VIEWS[view_name]) == MatReading(
        drawn=frozenset({"gap", "shortcut"}), slots={"tile": "bulb", "side": "wire"}
    )


@pytest.mark.parametrize("view_name", ALL_VIEWS)
@pytest.mark.parametrize("wrong_kind", ["resistor", "switch"])
def test_a_tile_the_slot_does_not_accept_reads_as_empty(view_name, wrong_kind, layout):
    reading = read(Scene(layout).place_tile("tile", wrong_kind), layout, VIEWS[view_name])
    assert reading.slots["tile"] == "empty"
    compose(layout, reading)  # the session composes every reading; it must not raise


@pytest.mark.parametrize("view_name", ALL_VIEWS)
def test_a_line_drawn_most_of_the_way_counts_and_a_short_stroke_does_not(view_name, layout):
    view = VIEWS[view_name]
    most = Scene(layout).draw_line("gap", fraction=0.6).draw_line("shortcut", fraction=0.6)
    short = Scene(layout).draw_line("gap", fraction=0.3).draw_line("shortcut", fraction=0.3)
    assert read(most, layout, view).drawn == {"gap", "shortcut"}
    assert read(short, layout, view).drawn == frozenset()


@pytest.mark.parametrize(
    "colour",
    [(0, 0, 0), (120, 40, 20), (40, 40, 160), (40, 90, 30), (70, 70, 70)],
    ids=["black", "blue", "red", "green", "soft-pencil"],
)
@pytest.mark.parametrize("view_name", ["straight", "harsh"])
def test_a_line_in_any_dark_colour_counts(colour, view_name, layout):
    scene = Scene(layout).draw_line("gap", colour=colour)
    assert read(scene, layout, VIEWS[view_name]).drawn == {"gap"}


@pytest.mark.parametrize("aside_mm", [-2.0, 2.0])
def test_a_line_drawn_a_little_off_the_guide_still_counts(aside_mm, layout):
    scene = Scene(layout).draw_line("gap", aside_mm=aside_mm)
    scene.draw_line("shortcut", aside_mm=aside_mm)
    assert read(scene, layout).drawn == {"gap", "shortcut"}


def test_a_thick_felt_pen_line_counts(layout):
    assert read(Scene(layout).draw_line("gap", width_mm=3.0), layout).drawn == {"gap"}


def test_a_tile_lying_roughly_on_its_slot_is_read(layout):
    scene = Scene(layout).place_tile("tile", "bulb", offset_mm=(4.0, -6.0))
    assert read(scene, layout).slots["tile"] == "bulb"


def test_a_tile_lying_far_from_any_slot_is_ignored(layout):
    scene = Scene(layout).place_tile("tile", "bulb", offset_mm=(-0.8 * DOT_PITCH_MM, 0.0))
    assert read(scene, layout).slots == {"tile": "empty", "side": "empty"}


def test_of_two_tiles_near_a_slot_the_nearer_one_is_read(layout):
    # A bulb dropped beside the slot while the wire tile is still on it, then the reverse.
    beside = (-13.2, 0.0)  # still within reach of the slot: half a dot pitch is 14 mm
    wire_on_slot = Scene(layout).place_tile("tile", "bulb", offset_mm=beside)
    wire_on_slot.place_tile("tile", "wire", offset_mm=(11.2, 0.0))
    assert read(wire_on_slot, layout).slots["tile"] == "wire"

    bulb_on_slot = Scene(layout).place_tile("tile", "wire", offset_mm=beside)
    bulb_on_slot.place_tile("tile", "bulb", offset_mm=(11.2, 0.0))
    assert read(bulb_on_slot, layout).slots["tile"] == "bulb"


def test_the_same_marker_seen_twice_is_read_wherever_it_lies(layout):
    # Two print-outs of the tiles sheet give two tiles with one marker id.
    scene = Scene(layout).place_tile("tile", "bulb", marker_id=10)
    scene.place_tile("side", "bulb", marker_id=10)
    assert read(scene, layout).slots == {"tile": "bulb", "side": "bulb"}


def test_a_blank_flattened_image_reads_as_an_empty_mat(layout, geometry):
    for image in (np.zeros((827, 1169), np.uint8), np.full((827, 1169), 255, np.uint8)):
        reading = read_mat(Flattened(image=image, frame_to_page=np.eye(3)), layout, geometry)
        assert reading == MatReading(slots={"tile": "empty", "side": "empty"})
