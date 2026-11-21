"""Reading the printed pieces: unit rules, then whole mats under bad light.

Rewritten on 22 Nov 2026 for the printed kit (six pieces, a two-colour battery, colour
squares on the mat). The tests it replaces were for one flat card colour per piece.
"""

from dataclasses import replace

import cv2
import numpy as np
import pytest
from vision_scenes import (
    AS_THE_CAMERA_SEES_RGB,
    BLUE_CAST,
    PRINTED_KINDS,
    PRINTED_RGB,
    READER_VIEWS,
    SKIN,
    STRAIGHT,
    TILTED,
    Scene,
)

from tacto.pieces import Placed
from tacto.vision.classify import (
    ColoursFileError,
    MatReader,
    Palette,
    PieceColours,
    Reading,
    classify_patch,
    load_colours,
    paper_colour,
    printed_palette,
    to_lab,
    to_placed,
)
from tacto.vision.flatten import flatten
from tacto.vision.patches import PATCH_LENGTH_PX, PATCH_WIDTH_PX, segments
from tacto.vision.print_geometry import REFERENCE_SQUARES

WHITE = np.float32([255.0, 255.0, 255.0])
PAPER = (255, 255, 255)


@pytest.fixture(scope="module")
def colours() -> PieceColours:
    return load_colours()


def bgr(name: str) -> tuple[int, int, int]:
    red, green, blue = PRINTED_RGB[name]
    return (blue, green, red)


def patch_of(*runs: tuple[tuple[int, int, int], float]) -> np.ndarray:
    """A patch as CIELAB, made of colours side by side, each a fraction of its length."""
    patch = np.full((PATCH_WIDTH_PX, PATCH_LENGTH_PX, 3), PAPER, np.uint8)
    start = 0.0
    for colour, fraction in runs:
        patch[:, round(start * PATCH_LENGTH_PX) : round((start + fraction) * PATCH_LENGTH_PX)] = (
            colour
        )
        start += fraction
    return to_lab(patch, WHITE)


def read_patch(colours, *runs) -> Reading:
    return classify_patch(patch_of(*runs), printed_palette(colours), colours)


# ---------- one patch ----------


@pytest.mark.parametrize("piece", ["wire", "bulb", "resistor", "switch_closed", "switch_open"])
def test_each_printed_colour_reads_as_its_piece(piece, colours):
    reading = read_patch(colours, (bgr(piece), 1.0))
    assert (reading.piece, reading.cover, reading.positive) == (piece, 1.0, None)


@pytest.mark.parametrize(
    "what, colour",
    [("paper", PAPER), ("a printed dot", (150, 150, 150)), ("a shadow", (170, 170, 170))],
)
def test_things_with_no_colour_read_as_empty(what, colour, colours):
    assert read_patch(colours, (colour, 1.0)).piece == "empty", what


def test_a_hand_over_the_segment_reads_as_unsure_not_as_a_piece_or_as_empty(colours):
    assert read_patch(colours, (SKIN, 1.0)).piece == "unsure"
    assert read_patch(colours, (bgr("wire"), 0.6), (SKIN, 0.4)).piece == "unsure"


def test_a_piece_needs_enough_of_the_patch_and_a_little_less_is_unsure(colours):
    assert read_patch(colours, (bgr("bulb"), colours.cover_fraction + 0.08)).piece == "bulb"
    assert read_patch(colours, (bgr("bulb"), colours.cover_fraction - 0.08)).piece == "unsure"
    assert read_patch(colours, (bgr("bulb"), colours.unsure_fraction - 0.08)).piece == "empty"


def test_the_symbol_printed_on_a_piece_does_not_change_what_it_is(colours):
    # A bulb's black cross and a resistor's white zigzag take a quarter of the patch.
    assert (
        read_patch(colours, (bgr("bulb"), 0.4), ((0, 0, 0), 0.25), (bgr("bulb"), 0.35)).piece
        == "bulb"
    )
    assert read_patch(colours, (bgr("resistor"), 0.75), (PAPER, 0.25)).piece == "resistor"


def test_a_battery_is_red_beside_black_and_its_red_end_is_positive(colours):
    red, black = bgr("battery_positive"), bgr("battery_negative")
    left = read_patch(colours, (red, 0.5), (black, 0.5))
    right = read_patch(colours, (black, 0.5), (red, 0.5))
    assert (left.piece, left.positive) == ("battery", "a")
    assert (right.piece, right.positive) == ("battery", "b")


def test_black_alone_is_not_a_piece_and_red_alone_is_not_yet_a_battery(colours):
    assert read_patch(colours, ((0, 0, 0), 0.8)).piece == "empty"
    assert read_patch(colours, (bgr("battery_positive"), 0.9)).piece == "unsure"


def test_two_colours_in_one_patch_read_as_the_larger(colours):
    assert (
        read_patch(colours, (bgr("wire"), 0.3), (bgr("switch_closed"), 0.7)).piece
        == "switch_closed"
    )


def test_paper_colour_is_the_papers_not_the_pieces(mat):
    scene = Scene(mat)
    for a, b in segments(mat)[:30]:
        scene.lay("wire", a, b)
    assert paper_colour(scene.page).tolist() == [255.0, 255.0, 255.0]
    tinted = (scene.page * np.float32([1.0, 0.8, 0.6])).astype(np.uint8)
    assert paper_colour(tinted).tolist() == [255.0, 204.0, 153.0]


def test_tinted_light_is_divided_out(colours):
    tint = np.float32([0.9, 0.7, 0.55])
    tinted = (np.full((4, 4, 3), bgr("switch_open"), np.float32) * tint).astype(np.uint8)
    plain = np.full((4, 4, 3), bgr("switch_open"), np.uint8)
    assert np.abs(to_lab(tinted, 255 * tint) - to_lab(plain, WHITE)).max() < 2.0


@pytest.mark.parametrize(
    "text, message",
    [
        ("colours:\n  wire: [0, 0, 255]\n", "no colour given for"),
        ("colours: {}\ncover_fraction: 2\n", "pieces.yaml"),
    ],
)
def test_a_colours_file_with_a_mistake_names_the_file(text, message, tmp_path):
    bad = tmp_path / "pieces.yaml"
    bad.write_text(text)
    with pytest.raises(ColoursFileError, match=message):
        load_colours(bad)
    with pytest.raises(ColoursFileError, match="cannot be read"):
        load_colours(tmp_path / "missing.yaml")


def test_the_colours_file_covers_every_square_on_the_mat(colours):
    assert set(colours.colours) == set(REFERENCE_SQUARES)


# ---------- whole mats ----------


def read(scene: Scene, view, mat, geometry, colours, seed=0, reader=None) -> dict[str, Reading]:
    reader = reader or MatReader(mat, geometry, colours)
    return reader.read(flatten(scene.photograph(view, seed=seed), geometry))


def kinds(readings: dict[str, Reading]) -> dict[str, str]:
    return {segment: r.piece for segment, r in readings.items() if r.piece != "empty"}


def seg(a, b) -> str:
    return Placed("wire", a, b).id


@pytest.mark.parametrize("view_name", READER_VIEWS)
def test_an_empty_mat_reads_as_empty(view_name, mat, geometry, colours):
    assert (
        kinds(read(Scene(mat, squares=True), READER_VIEWS[view_name], mat, geometry, colours)) == {}
    )


@pytest.mark.parametrize("view_name", READER_VIEWS)
def test_one_of_each_piece_reads_right_across_and_down(view_name, mat, geometry, colours):
    scene, expected = Scene(mat, squares=True), {}
    for index, kind in enumerate(PRINTED_KINDS):
        across = ((index, 1), (index + 1, 1))
        down = ((index + 1, 3), (index + 1, 4))
        for a, b in (across, down):
            scene.lay(kind, a, b)
            expected[seg(a, b)] = kind
    assert kinds(read(scene, READER_VIEWS[view_name], mat, geometry, colours)) == expected


@pytest.mark.parametrize("view", [STRAIGHT, TILTED, BLUE_CAST])
def test_a_batterys_positive_end_is_read_whichever_way_it_lies(view, mat, geometry, colours):
    scene = (
        Scene(mat, squares=True)
        .lay("battery", (1, 1), (2, 1), positive="a")
        .lay("battery", (4, 1), (5, 1), positive="b")
        .lay("battery", (2, 3), (2, 4), positive="a")
        .lay("battery", (6, 3), (6, 4), positive="b")
    )
    readings = read(scene, view, mat, geometry, colours)
    assert {s: r.positive for s, r in readings.items() if r.piece == "battery"} == {
        "1,1-2,1": "a",
        "4,1-5,1": "b",
        "2,3-2,4": "a",
        "6,3-6,4": "b",
    }


def test_the_squares_are_read_and_follow_the_light(mat, geometry, colours):
    reader = MatReader(mat, geometry, colours)
    assert not any(reader.palette.seen)
    read(Scene(mat, squares=True), STRAIGHT, mat, geometry, colours, reader=reader)
    assert all(reader.palette.seen)
    plain = reader.palette.lab.copy()
    # Dimmer, bluer light: after dividing by the paper the squares read nearly the same.
    read(
        Scene(mat, squares=True),
        replace(STRAIGHT, cast=(1.0, 0.86, 0.81)),
        mat,
        geometry,
        colours,
        reader=reader,
    )
    assert np.abs(reader.palette.lab - plain).max() < 6.0


def test_a_hand_over_a_square_does_not_become_that_colour(mat, geometry, colours):
    reader = MatReader(mat, geometry, colours)
    read(Scene(mat, squares=True), STRAIGHT, mat, geometry, colours, reader=reader)
    before = reader.palette.lab.copy()
    covered = Scene(mat, squares=True).lay("wire", (3, 2), (4, 2))
    squares = geometry.reference_square_centres_mm(mat.cols)
    for name in ("wire", "switch_open", "battery_negative"):
        covered.cover(squares[name], 9.0)
    readings = read(covered, STRAIGHT, mat, geometry, colours, reader=reader)
    assert np.array_equal(reader.palette.lab, before)
    assert kinds(readings) == {"3,2-4,2": "wire"}


def test_a_mat_without_squares_is_read_from_the_printed_colours(mat, geometry, colours):
    scene = Scene(mat).lay("wire", (1, 1), (2, 1)).lay("battery", (3, 1), (4, 1), positive="b")
    reader = MatReader(mat, geometry, colours)
    readings = read(scene, STRAIGHT, mat, geometry, colours, reader=reader)
    assert not any(reader.palette.seen)
    assert kinds(readings) == {"1,1-2,1": "wire", "3,1-4,1": "battery"}


def test_a_hand_on_the_mat_is_unsure_where_it_lies_and_right_elsewhere(mat, geometry, colours):
    scene = Scene(mat, squares=True).lay("bulb", (1, 1), (2, 1)).lay("resistor", (5, 3), (6, 3))
    x_mm, y_mm = np.mean([geometry.dot_mm((5, 3)), geometry.dot_mm((6, 3))], axis=0)
    scene.cover((float(x_mm), float(y_mm)), 22.0)
    readings = read(scene, TILTED, mat, geometry, colours)
    assert readings["1,1-2,1"].piece == "bulb"
    assert readings["5,3-6,3"].piece == "unsure"
    assert {r.piece for r in readings.values()} == {"empty", "bulb", "unsure"}


def random_layout(mat, rng: np.random.Generator) -> dict[tuple, tuple[str, str]]:
    """Between 6 and 20 pieces on random segments, every piece present: segment -> (kind, +end)."""
    every = segments(mat)
    count = int(rng.integers(6, 21))
    chosen = [every[i] for i in rng.choice(len(every), size=count, replace=False)]
    extra = [str(rng.choice(PRINTED_KINDS)) for _ in range(count - len(PRINTED_KINDS))]
    return {
        segment: (kind, str(rng.choice(["a", "b"])))
        for segment, kind in zip(chosen, [*PRINTED_KINDS, *extra], strict=True)
    }


def laid_out(mat, layout, rng: np.random.Generator) -> Scene:
    """As a person lays pieces: a couple of millimetres off and a few degrees round."""
    scene = Scene(mat, squares=True)
    for (a, b), (kind, positive) in layout.items():
        scene.lay(
            kind,
            a,
            b,
            positive=positive,
            offset_mm=tuple(rng.uniform(-2.0, 2.0, size=2)),
            turn_deg=float(rng.uniform(-6, 6)),
        )
    return scene


@pytest.mark.parametrize("view_name", READER_VIEWS)
def test_twenty_carelessly_laid_layouts_read_right(view_name, mat, geometry, colours):
    rng = np.random.default_rng(7)
    wrong: list[str] = []
    for number in range(20):
        layout = random_layout(mat, rng)
        scene = laid_out(mat, layout, rng)
        readings = read(scene, READER_VIEWS[view_name], mat, geometry, colours, seed=number)
        expected = {
            seg(a, b): (kind, positive if kind == "battery" else None)
            for (a, b), (kind, positive) in layout.items()
        }
        got = {s: (r.piece, r.positive) for s, r in readings.items() if r.piece != "empty"}
        if got != expected:
            differ = {
                s: (expected.get(s), got.get(s))
                for s in set(expected) | set(got)
                if expected.get(s) != got.get(s)
            }
            wrong.append(f"layout {number}: {differ}")
    assert not wrong, f"{len(wrong)} of 20 layouts misread under {view_name}: {wrong[:3]}"


# ---------- readings to pieces ----------


def test_readings_become_pieces_with_polarity_and_switch_state(mat):
    readings = {
        "0,0-1,0": Reading("wire", 0.9),
        "1,0-2,0": Reading("battery", 0.9, "b"),
        "2,0-2,1": Reading("battery", 0.9, "a"),
        "3,0-4,0": Reading("switch_closed", 0.8),
        "4,0-5,0": Reading("switch_open", 0.8),
        "5,0-6,0": Reading("bulb", 0.7),
        "6,0-7,0": Reading("resistor", 0.7),
        "7,0-8,0": Reading("unsure", 0.3),
        "0,1-1,1": Reading("empty", 0.0),
    }
    assert set(to_placed(readings, mat)) == {
        Placed("wire", (0, 0), (1, 0)),
        Placed("battery", (2, 0), (1, 0)),  # a is the positive end
        Placed("battery", (2, 0), (2, 1)),
        Placed("switch", (3, 0), (4, 0), closed=True),
        Placed("switch", (4, 0), (5, 0), closed=False),
        Placed("bulb", (5, 0), (6, 0)),
        Placed("resistor", (6, 0), (7, 0)),
    }


def test_blur_from_a_soft_focus_frame_still_reads_right(mat, geometry, colours):
    scene = Scene(mat, squares=True)
    for index, kind in enumerate(PRINTED_KINDS):
        scene.lay(kind, (index, 2), (index + 1, 2))
    frame = cv2.GaussianBlur(scene.photograph(TILTED), (0, 0), 3.0)
    readings = MatReader(mat, geometry, colours).read(
        # The position is known from before; only the picture is soft.
        replace(
            flatten(scene.photograph(TILTED), geometry), image=flatten_with(frame, scene, geometry)
        )
    )
    assert [readings[seg((i, 2), (i + 1, 2))].piece for i in range(6)] == list(PRINTED_KINDS)


def flatten_with(frame: np.ndarray, scene: Scene, geometry) -> np.ndarray:
    from tacto.vision.flatten import warp

    sharp = flatten(scene.photograph(TILTED), geometry)
    return warp(frame, sharp.frame_to_page).image


# ---------- shadows, with the colours as the real camera sees them ----------
# Reported on the real mat on 22 Nov 2026: after working well, wires began to read as
# open switches. The squares are at the edge nearest the learner, under their arms.


def camera_scene(mat) -> tuple[Scene, dict[str, str]]:
    """One of each piece twice over, in the colours the demo camera sees."""
    scene, expected = Scene(mat, squares=True, rgb=AS_THE_CAMERA_SEES_RGB), {}
    for index, kind in enumerate(PRINTED_KINDS):
        for a, b in (((index + 1, 2), (index + 2, 2)), ((index + 1, 3), (index + 1, 4))):
            scene.lay(kind, a, b)
            expected[seg(a, b)] = kind
    return scene, expected


def test_the_cameras_own_colours_read_right_in_even_light(mat, geometry, colours):
    scene, expected = camera_scene(mat)
    assert kinds(read(scene, TILTED, mat, geometry, colours)) == expected


@pytest.mark.parametrize("light", [0.85, 0.7, 0.55])
def test_a_shadow_over_the_squares_does_not_change_what_the_pieces_are(
    light, mat, geometry, colours
):
    reader = MatReader(mat, geometry, colours)
    scene, expected = camera_scene(mat)
    read(scene, TILTED, mat, geometry, colours, reader=reader)
    shaded, _ = camera_scene(mat)
    shaded.shade((30.0, 0.0), (267.0, 26.0), light)  # an arm over the row of squares
    for _ in range(5):  # the shadow stays: the references must not walk off with it
        readings = read(shaded, TILTED, mat, geometry, colours, reader=reader)
    assert kinds(readings) == expected


@pytest.mark.parametrize("light", [0.85, 0.7, 0.55])
def test_a_shadow_there_from_the_first_frame_does_not_either(light, mat, geometry, colours):
    shaded, expected = camera_scene(mat)
    shaded.shade((30.0, 0.0), (267.0, 26.0), light)
    assert kinds(read(shaded, TILTED, mat, geometry, colours)) == expected


@pytest.mark.parametrize("light", [0.85, 0.7, 0.55])
def test_a_shadow_over_the_pieces_does_not_change_what_they_are(light, mat, geometry, colours):
    scene, expected = camera_scene(mat)
    scene.shade((30.0, 75.0), (267.0, 160.0), light)  # across the two rows of pieces
    assert kinds(read(scene, TILTED, mat, geometry, colours)) == expected


def test_a_shadow_creeping_over_the_squares_does_not_walk_the_references_away(
    mat, geometry, colours
):
    reader = MatReader(mat, geometry, colours)
    _, expected = camera_scene(mat)
    for light in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55):
        shaded, _ = camera_scene(mat)
        shaded.shade((30.0, 0.0), (267.0, 26.0), light)
        for _ in range(2):
            readings = read(shaded, TILTED, mat, geometry, colours, reader=reader)
        assert kinds(readings) == expected, f"at {light:.0%} light"


def test_a_square_with_a_sleeve_beside_it_is_not_read(mat, geometry, colours):
    reader = MatReader(mat, geometry, colours)
    scene, _ = camera_scene(mat)
    read(scene, TILTED, mat, geometry, colours, reader=reader)
    before = reader.palette.lab.copy()
    covered, expected = camera_scene(mat)
    x, y = geometry.reference_square_centres_mm(mat.cols)["wire"]
    # Something dark lying across the paper round the wire square, leaving the square bare.
    covered.shade((x - 14.0, y - 14.0), (x - 7.0, y + 14.0), 0.2)
    covered.shade((x + 7.0, y - 14.0), (x + 14.0, y + 14.0), 0.2)
    readings = read(covered, TILTED, mat, geometry, colours, reader=reader)
    assert np.array_equal(reader.palette.lab[0], before[0])
    assert kinds(readings) == expected


# ---------- values measured off the real mat ----------
# The seven squares as the demo camera read them on 22 Nov 2026 (GET /debug/reader), and
# the mean colour of real pieces' pixels in the same frame. CIELAB with the paper as white.

REAL_SQUARES = Palette(
    lab=np.float32(
        [
            [22.8, 21.0, -45.4],  # wire
            [89.2, -5.7, 82.0],  # bulb
            [47.4, 71.6, 25.5],  # resistor
            [35.3, -32.8, 17.2],  # switch_closed
            [37.1, 3.2, -41.5],  # switch_open
            [46.1, 69.6, 59.9],  # battery_positive
            [4.6, -1.3, 2.2],  # battery_negative
        ]
    ),
    seen=(True,) * 7,
)


def lab_patch(lab: tuple[float, float, float]) -> np.ndarray:
    return np.full((PATCH_WIDTH_PX, PATCH_LENGTH_PX, 3), lab, np.float32)


@pytest.mark.parametrize(
    "lab",
    [
        (25.0, 12.0, -33.0),  # the two wires that split 52% wire to 42% open switch
        (23.0, 13.0, -33.0),
        (18.0, 17.0, -35.0),
        (26.0, 18.0, -42.0),
        (30.0, 11.0, -30.0),  # paler still: the same hue, washed out further
        (15.0, 12.0, -27.0),  # and in shadow
    ],
)
def test_a_washed_out_or_shaded_real_wire_is_still_a_wire(lab, colours):
    assert classify_patch(lab_patch(lab), REAL_SQUARES, colours).piece == "wire"


@pytest.mark.parametrize(
    "lab",
    [(37.0, 3.0, -41.0), (30.0, 1.0, -31.0), (44.0, 5.0, -44.0), (25.0, 2.0, -28.0)],
)
def test_a_real_open_switch_bright_or_shaded_is_still_an_open_switch(lab, colours):
    assert classify_patch(lab_patch(lab), REAL_SQUARES, colours).piece == "switch_open"


def test_skin_is_still_not_a_piece_with_the_real_squares(colours):
    # Skin's hue lies between the red and yellow squares; it is far too pale to be either.
    for skin in [(70.0, 15.0, 22.0), (60.0, 18.0, 20.0), (80.0, 10.0, 18.0)]:
        assert classify_patch(lab_patch(skin), REAL_SQUARES, colours).piece == "unsure"


@pytest.mark.parametrize(
    "square, piece",
    [(1, "bulb"), (2, "resistor"), (3, "switch_closed"), (0, "wire"), (4, "switch_open")],
)
def test_each_real_square_reads_as_its_own_piece_at_three_quarters_strength(square, piece, colours):
    lightness, a, b = REAL_SQUARES.lab[square]
    faded = (float(lightness), float(a) * 0.75, float(b) * 0.75)
    assert classify_patch(lab_patch(faded), REAL_SQUARES, colours).piece == piece
