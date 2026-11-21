"""Telling the pieces apart by colour: unit rules, then whole mats under bad conditions."""

import numpy as np
import pytest
from vision_scenes import CARD, SKIN, STRAIGHT, VIEWS, Scene

from tacto.vision.classify import (
    ColoursFileError,
    HueRange,
    PieceColours,
    classify_mat,
    classify_patch,
    load_colours,
    paper_brightness,
)
from tacto.vision.flatten import flatten
from tacto.vision.patches import PATCH_LENGTH_PX, PATCH_WIDTH_PX, segments

PIECES = ("wire", "battery", "bulb", "resistor", "switch")
PAPER = (255, 255, 255)


@pytest.fixture(scope="module")
def colours() -> PieceColours:
    return load_colours()


def solid(colour) -> np.ndarray:
    return np.full((PATCH_WIDTH_PX, PATCH_LENGTH_PX, 3), colour, np.uint8)


def part_covered(colour, fraction: float) -> np.ndarray:
    patch = solid(PAPER)
    patch[:, : round(PATCH_LENGTH_PX * fraction)] = colour
    return patch


@pytest.mark.parametrize("piece", PIECES)
def test_each_card_colour_reads_as_its_piece(piece, colours):
    reading = classify_patch(solid(CARD[piece]), colours)
    assert (reading.piece, reading.cover) == (piece, 1.0)


@pytest.mark.parametrize(
    "what, colour",
    [
        ("paper", PAPER),
        ("a printed dot", (150, 150, 150)),
        ("a shadow", (150, 150, 150)),
        ("skin", SKIN),
    ],
)
def test_things_that_are_not_card_read_as_empty(what, colour, colours):
    assert classify_patch(solid(colour), colours).piece == "empty", what


def test_a_piece_must_cover_half_the_patch(colours):
    assert classify_patch(part_covered(CARD["bulb"], 0.6), colours).piece == "bulb"
    reading = classify_patch(part_covered(CARD["bulb"], 0.4), colours)
    assert reading.piece == "empty" and reading.cover == pytest.approx(0.4, abs=0.03)


def test_two_colours_in_one_patch_read_as_the_larger(colours):
    patch = part_covered(CARD["battery"], 0.3)
    patch[:, round(PATCH_LENGTH_PX * 0.3) :] = CARD["switch"]
    assert classify_patch(patch, colours).piece == "switch"


def test_red_wraps_through_zero_on_the_colour_wheel():
    red = HueRange(hue_deg=(340, 15))
    assert red.contains(np.array([350.0, 0.0, 10.0, 20.0, 180.0])).tolist() == [
        True,
        True,
        True,
        False,
        False,
    ]


@pytest.mark.parametrize("light", [1.0, 0.7, 0.5, 0.35])
def test_a_dim_room_does_not_turn_paper_into_wire(light, colours):
    """Darkness is judged against the paper, so the answer holds as the light drops."""
    paper = 255 * light
    dim = lambda colour: solid(tuple(round(c * light) for c in colour))  # noqa: E731
    assert classify_patch(dim(PAPER), colours, paper=paper).piece == "empty"
    for piece in PIECES:
        assert classify_patch(dim(CARD[piece]), colours, paper=paper).piece == piece


def test_paper_brightness_is_the_papers_not_the_pieces(mat):
    scene = Scene(mat)
    for a, b in segments(mat)[:30]:
        scene.place("wire", a, b)
    assert paper_brightness(scene.page) == 255
    assert paper_brightness((scene.page * 0.6).astype(np.uint8)) == pytest.approx(153, abs=1)


def test_a_colours_file_with_a_mistake_names_the_file(tmp_path):
    bad = tmp_path / "pieces.yaml"
    bad.write_text("pieces:\n  laser: dark\n")
    with pytest.raises(ColoursFileError, match="pieces.yaml"):
        load_colours(bad)
    bad.write_text("pieces:\n  wire: dark\n  bulb: dark\n")
    with pytest.raises(ColoursFileError, match="only one"):
        load_colours(bad)
    with pytest.raises(ColoursFileError, match="cannot be read"):
        load_colours(tmp_path / "missing.yaml")


# ---------- whole mats ----------


def random_layout(mat, rng: np.random.Generator) -> dict[tuple, str]:
    """Between 6 and 20 pieces on random segments, every piece type present."""
    every = segments(mat)
    count = int(rng.integers(6, 21))
    chosen = [every[i] for i in rng.choice(len(every), size=count, replace=False)]
    types = list(PIECES) + [str(rng.choice(PIECES)) for _ in range(count - len(PIECES))]
    return dict(zip(chosen, types, strict=True))


def laid_out(mat, layout, rng: np.random.Generator | None = None) -> Scene:
    scene = Scene(mat)
    for (a, b), piece in layout.items():
        if rng is None:
            scene.place(piece, a, b)
        else:  # as a person lays card: a couple of millimetres off and a few degrees round
            scene.place(
                piece,
                a,
                b,
                offset_mm=tuple(rng.uniform(-2.0, 2.0, size=2)),
                turn_deg=float(rng.uniform(-6, 6)),
            )
    return scene


def read(scene: Scene, view, mat, geometry, colours, seed=0) -> dict[str, str]:
    flattened = flatten(scene.photograph(view, seed=seed), geometry)
    return {s: r.piece for s, r in classify_mat(flattened, mat, geometry, colours).items()}


def expected(mat, layout) -> dict[str, str]:
    from tacto.contract import segment_id

    truth = {segment_id(a, b): "empty" for a, b in segments(mat)}
    truth.update({segment_id(a, b): piece for (a, b), piece in layout.items()})
    return truth


def test_an_empty_mat_reads_as_empty_everywhere(mat, geometry, colours):
    for view in VIEWS.values():
        assert set(read(Scene(mat), view, mat, geometry, colours).values()) == {"empty"}


@pytest.mark.parametrize("view_name", VIEWS)
def test_twenty_layouts_read_correctly(view_name, mat, geometry, colours):
    """Twenty random layouts, carelessly laid, every segment right, in every view."""
    rng = np.random.default_rng(101)
    for index in range(20):
        layout = random_layout(mat, rng)
        scene = laid_out(mat, layout, rng)
        got = read(scene, VIEWS[view_name], mat, geometry, colours, seed=index)
        wrong = {s: (want, got[s]) for s, want in expected(mat, layout).items() if got[s] != want}
        assert wrong == {}, f"layout {index} in view {view_name}"


def test_a_full_mat_reads_correctly(mat, geometry, colours):
    """Every segment covered: the paper's brightness must not be taken from the card."""
    layout = {seg: PIECES[i % 5] for i, seg in enumerate(segments(mat))}
    got = read(laid_out(mat, layout), STRAIGHT, mat, geometry, colours)
    assert got == expected(mat, layout)


def test_a_hand_over_the_mat_reads_as_empty_not_as_a_piece(mat, geometry, colours):
    """Skin is not a piece. (Holding what was under the hand is the stability step's job.)"""
    scene = laid_out(mat, {((2, 1), (3, 1)): "bulb"})
    scene.cover(geometry.dot_mm((5, 3)), 30.0)
    got = read(scene, STRAIGHT, mat, geometry, colours)
    assert got["2,1-3,1"] == "bulb"
    assert {piece for seg, piece in got.items() if seg != "2,1-3,1"} == {"empty"}
