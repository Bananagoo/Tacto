import json

from fastapi.testclient import TestClient

from tacto.contract_v2 import State
from tacto_mock.main import create_mock_app
from tacto_mock.sample import SAMPLE_PATH, sample_text
from tacto_mock.scenario import BATTERY_WIRE, BULB_A, states


def test_committed_sample_matches_the_scenario():
    """If this fails, run `make sample` and commit the result."""
    assert SAMPLE_PATH.read_text() == sample_text()


def test_every_recorded_line_is_a_valid_state():
    lines = SAMPLE_PATH.read_text().splitlines()
    parsed = [State.model_validate_json(line) for line in lines]
    assert [state.seq for state in parsed] == list(range(len(lines)))


def test_the_run_shows_everything_the_ui_must_draw():
    run = list(states())
    assert {s.circuit.status for s in run} == {"open", "working", "shorted"}
    assert {p.type for s in run for p in s.pieces} == {
        "wire",
        "battery",
        "bulb",
        "resistor",
        "switch",
    }
    assert {p.closed for s in run for p in s.pieces if p.type == "switch"} == {True, False}
    assert any(not s.mat_visible for s in run)
    assert any(s.touch.buzz for s in run)
    assert any(s.circuit.shorted_path for s in run)
    assert {s.lesson.step_index for s in run} == {0, 1, 2, 3, 4}
    assert run[-1].lesson.lesson_done
    assert {s.circuit.voltage for s in run} >= {6.0, 9.0}


def test_the_pulse_follows_the_lesson_plan():
    """3 Hz for one bulb, 1.5 Hz in series, 6 Hz on the battery wire in parallel."""
    run = list(states())

    def pulses(step: int, piece_id: str) -> set[float]:
        return {
            s.touch.pulse_hz
            for s in run
            if s.lesson.step_index == step
            and s.touch.piece_id == piece_id
            and s.circuit.voltage == 6.0
            and s.circuit.status == "working"
        }

    assert pulses(1, BULB_A) == {3.0}
    assert pulses(2, BULB_A) == {1.5}
    assert pulses(3, BATTERY_WIRE) == {5.99}  # 6 / 5.009 ohms with the wires' resistance


def test_mock_replays_loops_and_keeps_counting(tmp_path):
    short = tmp_path / "two.jsonl"
    short.write_text("\n".join(SAMPLE_PATH.read_text().splitlines()[:2]) + "\n")
    app = create_mock_app(short, state_hz=200)
    client = TestClient(app)
    assert client.get("/health").json() == {"ok": True, "source": "replay", "states": 2}
    with client.websocket_connect("/ws") as ws:
        ws.send_text('{"type":"set_voltage","volts":7.5}')
        ws.send_text("not json")  # logged, not fatal
        seen = [json.loads(ws.receive_text()) for _ in range(5)]
    assert [s["seq"] for s in seen] == [0, 1, 2, 3, 4]
    assert seen[0]["pieces"] == seen[2]["pieces"] == seen[4]["pieces"]
    assert all(State.model_validate(s) for s in seen)
