import json

from fastapi.testclient import TestClient

from tacto.contract import State
from tacto_mock.main import create_mock_app
from tacto_mock.sample import SAMPLE_PATH, sample_text
from tacto_mock.scenario import BATTERY, BULB_A, states


def test_committed_sample_matches_the_scenario():
    """If this fails, run `make sample` and commit the result."""
    assert SAMPLE_PATH.read_text() == sample_text()


def test_every_recorded_line_is_a_valid_state():
    lines = SAMPLE_PATH.read_text().splitlines()
    parsed = [State.model_validate_json(line) for line in lines]
    assert [state.seq for state in parsed] == list(range(len(lines)))


def test_the_run_follows_the_demo_without_a_short():
    run = list(states())
    assert {s.circuit.status for s in run} == {"open", "working"}
    assert {p.type for s in run for p in s.pieces} == {
        "wire",
        "battery",
        "bulb",
        "switch",
    }
    assert {p.closed for s in run for p in s.pieces if p.type == "switch"} == {True, False}
    assert any(not s.mat_visible for s in run)
    assert not any(s.touch.buzz for s in run)
    assert {s.lesson.step_index for s in run} == set(range(6))
    assert run[-1].lesson.lesson_done
    assert {s.circuit.voltage for s in run} >= {3.0, 6.0}
    assert len({s.lesson.reflection for s in run if s.lesson.reflection}) == 3


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

    assert pulses(3, BULB_A) == {3.0}
    assert pulses(4, BULB_A) >= {1.5}
    assert pulses(5, BATTERY) == {5.99}  # 6 / 5.009 ohms with the wires' resistance


def test_mock_waits_for_reflection_and_restarts(tmp_path):
    run = list(states())
    reflection = next(s for s in run if s.lesson.reflection)
    following = next(s for s in run if s.lesson.step_id == "series")
    sample = tmp_path / "reflection.jsonl"
    sample.write_text(reflection.model_dump_json() + "\n" + following.model_dump_json() + "\n")
    client = TestClient(create_mock_app(sample, state_hz=200))
    with client.websocket_connect("/ws") as ws:
        for _ in range(3):
            assert json.loads(ws.receive_text())["lesson"]["step_id"] == "raise_voltage"
        ws.send_json({"type": "continue_lesson", "step_id": "raise_voltage"})
        assert any(
            json.loads(ws.receive_text())["lesson"]["step_id"] == "series" for _ in range(10)
        )
        ws.send_json({"type": "set_mode", "mode": "tinker"})
        assert any(json.loads(ws.receive_text())["mode"] == "tinker" for _ in range(10))
        ws.send_json({"type": "restart_lesson"})
        seen = [json.loads(ws.receive_text()) for _ in range(4)]
        assert seen[-1]["mode"] == "lab" and seen[-1]["lesson"]["step_id"] == "raise_voltage"


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
