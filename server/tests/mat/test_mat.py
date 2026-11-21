"""The mat model: loading a layout, and turning a reading of it into a circuit."""

import pytest

from tacto.mat.compose import compose
from tacto.mat.loader import MatFileError, load_mat
from tacto.mat.locate import element_at
from tacto.mat.models import MatLayout, MatReading
from tacto.platform import MATS_DIR
from tacto.sim import solve_circuit


@pytest.fixture(scope="module")
def layout() -> MatLayout:
    return load_mat(MATS_DIR / "circuits-101.yaml")


def solved(layout: MatLayout, reading: MatReading):
    parts, wires = compose(layout, reading)
    return solve_circuit(parts, wires, layout.battery_volts)


def test_the_kit_starts_as_an_open_circuit_with_one_bulb(layout):
    circuit = solved(layout, layout.initial_reading())
    assert circuit.status == "open"
    assert [part.kind for part in circuit.parts] == ["battery", "bulb"]


def test_drawing_the_gap_lights_bulb_a(layout):
    reading = layout.initial_reading().model_copy(update={"drawn": frozenset({"gap"})})
    circuit = solved(layout, reading)
    assert (circuit.status, circuit.topology) == ("closed", "single")


def test_a_bulb_in_the_tile_slot_is_in_series(layout):
    reading = MatReading(drawn=frozenset({"gap"}), slots={"tile": "bulb", "side": "empty"})
    circuit = solved(layout, reading)
    assert circuit.topology == "series"
    assert {part.id for part in circuit.parts} == {"battery", "bulb_a", "bulb@tile"}


def test_a_bulb_in_the_side_slot_is_in_parallel(layout):
    reading = MatReading(drawn=frozenset({"gap"}), slots={"tile": "wire", "side": "bulb"})
    assert solved(layout, reading).topology == "parallel"


def test_the_shortcut_line_shorts_the_battery(layout):
    reading = MatReading(drawn=frozenset({"gap", "shortcut"}), slots={"tile": "wire"})
    assert solved(layout, reading).status == "short"


def test_a_slot_missing_from_the_reading_is_empty(layout):
    parts, _ = compose(layout, MatReading())
    assert [part.id for part in parts] == ["battery", "bulb_a"]


@pytest.mark.parametrize(
    "reading",
    [
        MatReading(drawn=frozenset({"moat"})),  # no such line on this mat
        MatReading(slots={"attic": "bulb"}),  # no such slot
        MatReading(slots={"tile": "switch"}),  # the slot does not take that tile
    ],
)
def test_a_reading_that_does_not_fit_the_mat_is_an_error(layout, reading):
    with pytest.raises(ValueError):
        compose(layout, reading)


def test_readings_compare_by_value(layout):
    assert layout.initial_reading() == layout.initial_reading()
    assert MatReading(drawn=frozenset({"gap"})) != MatReading()


def mat(**changes) -> dict:
    data = {
        "id": "tiny",
        "cols": 3,
        "rows": 2,
        "battery_volts": 6.0,
        "parts": [{"id": "battery", "kind": "battery", "a": [0, 0], "b": [0, 1]}],
        "slots": [{"id": "s", "a": [1, 0], "b": [2, 0], "accepts": ["bulb"]}],
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    "bad",
    [
        {"wires": [{"a": [0, 0], "b": [3, 0]}]},  # off the grid
        {"drawables": [{"id": "s", "a": [0, 0], "b": [1, 0]}]},  # id already used by a slot
        {"slots": [{"id": "s", "a": [1, 0], "b": [2, 0], "accepts": ["bulb"], "starts": "wire"}]},
        {"battery_volts": 0},
        {"colz": 3},  # typo in a key
    ],
)
def test_a_mat_file_with_a_mistake_is_rejected(bad):
    with pytest.raises(ValueError):
        MatLayout.model_validate(mat(**bad))


def test_a_broken_mat_file_names_itself(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("id: [unclosed")
    with pytest.raises(MatFileError, match="broken.yaml"):
        load_mat(path)
    with pytest.raises(MatFileError, match="missing.yaml"):
        load_mat(tmp_path / "missing.yaml")


# ---------- which element is a fingertip on ----------


def at(layout: MatLayout, reading: MatReading, col: float, row: float):
    parts, wires = compose(layout, reading)
    return element_at(
        parts,
        wires,
        cols=layout.cols,
        rows=layout.rows,
        x=col / (layout.cols - 1),
        y=row / (layout.rows - 1),
    )


def test_a_fingertip_on_a_wire_finds_that_wire(layout):
    wire = at(layout, layout.initial_reading(), 1.5, 0.1)
    assert (wire.a, wire.b) == ((1, 0), (2, 0))


def test_a_fingertip_on_a_part_finds_the_part_not_the_wire_entering_it(layout):
    assert at(layout, layout.initial_reading(), 5, 0).id == "bulb_a"
    assert at(layout, layout.initial_reading(), 4.05, 0).id == "bulb_a"


def test_a_fingertip_away_from_everything_finds_nothing(layout):
    assert at(layout, layout.initial_reading(), 5, 2.5) is None


def test_an_undrawn_line_cannot_be_touched(layout):
    assert at(layout, layout.initial_reading(), 5, 4) is None
    drawn = layout.initial_reading().model_copy(update={"drawn": frozenset({"gap"})})
    assert at(layout, drawn, 5, 4) is not None
