import pytest
from fastapi.testclient import TestClient

from tacto.app import create_lab_app
from tacto.contract import Grid, SetVoltage, State
from tacto.lab import Lab, MatView, piece_at
from tacto.pieces import solve_pieces
from tacto_mock.scenario import BULB_A, loop

GRID = Grid(cols=9, rows=6)


class FixedMat:
    def __init__(self, view: MatView | None = None) -> None:
        self.current = view or MatView()

    def view(self) -> MatView:
        return self.current


def test_an_empty_mat_is_open_and_silent():
    state = Lab(GRID, FixedMat(), source_name="manual").state()
    assert state.circuit.status == "open"
    assert state.pieces == [] and not state.touch.present
    assert state.source == "manual" and state.grid == GRID


def test_seq_counts_and_time_comes_from_the_clock():
    ticks = iter([10.0, 10.5, 12.0])
    lab = Lab(GRID, FixedMat(), source_name="manual", now=lambda: next(ticks))
    first, second = lab.state(), lab.state()
    assert (first.seq, first.t) == (0, 0.5)
    assert (second.seq, second.t) == (1, 2.0)


def test_voltage_from_the_browser_changes_the_current():
    """10 ohms: 3 V gives 0.3 A, 9 V gives 0.9 A."""
    lab = Lab(GRID, FixedMat(MatView(tuple(loop(closed=True)))), source_name="manual")
    assert lab.state().circuit.total_current == pytest.approx(0.3, abs=0.001)
    lab.handle(SetVoltage(volts=9))
    state = lab.state()
    assert state.circuit.voltage == 9
    assert state.circuit.total_current == pytest.approx(0.9, abs=0.001)


def test_the_circuit_is_solved_only_when_something_changes(monkeypatch):
    calls = []

    def counting(placed, volts):
        calls.append(volts)
        return solve_pieces(placed, volts)

    monkeypatch.setattr("tacto.lab.solve_pieces", counting)
    mat = FixedMat(MatView(tuple(loop(closed=True))))
    lab = Lab(GRID, mat, source_name="manual")
    for _ in range(5):
        lab.state()
    assert calls == [3.0]
    mat.current = MatView(tuple(loop(closed=False)))
    lab.state()
    lab.handle(SetVoltage(volts=7))
    lab.state()
    assert calls == [3.0, 3.0, 7.0]


def test_a_finger_on_the_bulb_feels_its_current():
    """Bulb A lies from dot (2,1) to (3,1); its middle is x = 2.5/8, y = 1/5."""
    view = MatView(tuple(loop(closed=True)), finger=(2.5 / 8, 1 / 5))
    touch = Lab(GRID, FixedMat(view), source_name="manual").state().touch
    assert touch.piece_id == BULB_A
    assert touch.pulse_hz == pytest.approx(1.5, abs=0.01)


def test_a_finger_away_from_every_piece_touches_nothing():
    view = MatView(tuple(loop(closed=True)), finger=(0.9, 0.9))
    touch = Lab(GRID, FixedMat(view), source_name="manual").state().touch
    assert touch.present and touch.piece_id is None and touch.pulse_hz == 0


def test_reach_is_about_a_third_of_a_dot():
    pieces, _ = solve_pieces(loop(closed=True), 6.0)
    on_bulb_y = 1 / 5
    assert piece_at(pieces, GRID, 2.5 / 8, on_bulb_y + 0.3 / 5).id == BULB_A
    assert piece_at(pieces, GRID, 2.5 / 8, on_bulb_y + 0.4 / 5) is None


def test_mat_not_visible_is_passed_through():
    view = MatView(tuple(loop(closed=True)), mat_visible=False)
    state = Lab(GRID, FixedMat(view), source_name="camera").state()
    assert state.mat_visible is False and len(state.pieces) == 10


def test_the_app_streams_states_and_takes_the_voltage():
    lab = Lab(GRID, FixedMat(MatView(tuple(loop(closed=True)))), source_name="manual")
    client = TestClient(create_lab_app(lab, source="manual", state_hz=200))
    assert client.get("/health").json() == {"ok": True, "source": "manual"}
    with client.websocket_connect("/ws") as ws:
        assert State.model_validate_json(ws.receive_text()).circuit.voltage == 3.0
        ws.send_text("nonsense")  # logged, not fatal
        ws.send_text('{"type":"set_voltage","volts":8.5}')
        for _ in range(50):
            if State.model_validate_json(ws.receive_text()).circuit.voltage == 8.5:
                break
        else:
            pytest.fail("the voltage never reached the state")
        ws.send_text('{"type":"set_mode","mode":"lab"}')
        for _ in range(50):
            state = State.model_validate_json(ws.receive_text())
            if state.mode == "lab":
                assert state.circuit.voltage == 3
                break
        else:
            pytest.fail("Lab mode never reached the state")
        ws.send_text('{"type":"set_voltage","volts":7}')
        for _ in range(50):
            if State.model_validate_json(ws.receive_text()).circuit.voltage == 7:
                break
        else:
            pytest.fail("voltage never changed")
        ws.send_text('{"type":"restart_lesson"}')
        for _ in range(50):
            if State.model_validate_json(ws.receive_text()).circuit.voltage == 3:
                break
        else:
            pytest.fail("restart did not restore the voltage")
