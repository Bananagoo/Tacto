import json

import pytest
from pydantic import ValidationError

from tacto.contract_export import CONTRACT_DIR, contract_files, example_state
from tacto.contract_v2 import Grid, Piece, SetVoltage, State, segment_id


def test_segment_id_is_the_same_for_either_order():
    assert segment_id((3, 1), (2, 1)) == segment_id((2, 1), (3, 1)) == "2,1-3,1"
    assert segment_id((4, 3), (4, 2)) == "4,2-4,3"


def test_a_piece_must_lie_between_neighbouring_dots():
    with pytest.raises(ValidationError, match="not neighbouring"):
        Piece(id="1,1-3,1", type="wire", a=(1, 1), b=(3, 1))
    with pytest.raises(ValidationError, match="not neighbouring"):
        Piece(id="1,1-2,2", type="wire", a=(1, 1), b=(2, 2))


def test_a_piece_id_must_match_its_segment():
    with pytest.raises(ValidationError, match="does not match"):
        Piece(id="bulb_a", type="bulb", a=(1, 1), b=(2, 1))


def test_a_battery_keeps_its_positive_end_first_whatever_its_id_order():
    battery = Piece(id="1,1-1,2", type="battery", a=(1, 2), b=(1, 1))
    assert battery.a == (1, 2)


def test_an_empty_mat_is_a_valid_open_state():
    state = State(t=0.0, grid=Grid(cols=9, rows=6))
    assert state.circuit.status == "open"
    assert state.pieces == []
    assert state.touch.piece_id is None


def test_state_survives_a_round_trip_through_json():
    state = example_state()
    assert State.model_validate_json(state.model_dump_json()) == state


def test_the_example_touches_a_piece_that_exists():
    state = example_state()
    assert state.touch.piece_id in {piece.id for piece in state.pieces}


def test_voltage_is_bounded():
    assert SetVoltage.model_validate_json('{"type":"set_voltage","volts":6.5}').volts == 6.5
    with pytest.raises(ValidationError):
        SetVoltage(volts=-1)
    with pytest.raises(ValidationError):
        SetVoltage(volts=12)


def test_committed_contract_files_are_up_to_date():
    """If this fails, run `make contract` and commit the result."""
    for name, expected in contract_files().items():
        committed = (CONTRACT_DIR / name).read_text()
        assert json.loads(committed) == json.loads(expected), name
