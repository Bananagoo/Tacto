"""The whole product without hardware: a scripted mat, the real solver, the real lesson
engine and a real (in-memory) database, played through all five steps of Circuits 101."""

from datetime import UTC, datetime, timedelta

import pytest

from tacto.contract import Answer, Next, State, Wheel
from tacto.mat.models import MatReading
from tacto.observation import Fingertip, Observation
from tacto.platform import Platform, open_platform
from tacto.session import Session


class ScriptedMat:
    """A Source the test moves by hand."""

    def __init__(self, reading: MatReading) -> None:
        self.reading = reading
        self.fingertip: Fingertip | None = None

    def observe(self) -> Observation:
        return Observation(reading=self.reading, fingertip=self.fingertip)

    def draw(self, line: str) -> None:
        self.reading = self.reading.model_copy(update={"drawn": self.reading.drawn | {line}})

    def put(self, slot: str, content: str) -> None:
        self.reading = self.reading.model_copy(
            update={"slots": {**self.reading.slots, slot: content}}
        )

    def touch(self, col: float, row: float, *, cols: int = 9, rows: int = 6) -> None:
        self.fingertip = Fingertip(x=col / (cols - 1), y=row / (rows - 1))


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(milliseconds=66)  # one state message later
        return self.now


@pytest.fixture
def platform() -> Platform:
    return open_platform(database_url="sqlite://")


def start(platform: Platform, nickname: str = "Ada") -> tuple[Session, ScriptedMat]:
    mat = ScriptedMat(platform.layout.initial_reading())
    session = Session(
        lesson=platform.lesson,
        layout=platform.layout,
        source=mat,
        source_name="mock",
        learner_id=platform.learners.get_or_create(nickname),
        learners=platform.learners,
        clock=Clock(),
    )
    return session, mat


def see_and_explain(session: Session) -> State:
    """Leave the test phase, read the explanation, and move to the next step."""
    session.handle(Next())
    explained = session.state()
    assert explained.tutor.phase == "explain"
    session.handle(Next())
    return explained


BATTERY_WIRE = (1.5, 0)  # on the top rail, between the battery and the first junction
BULB_A_WIRE = (6.5, 0)  # just after bulb A
SIDE_WIRE = (3, 0.5)  # the side branch, above its slot
SHORTCUT = (2, 2)  # the middle of the line that shorts the battery


def test_a_learner_plays_the_whole_lesson(platform):
    session, mat = start(platform)

    # Setup: the kit as it ships is an open circuit, and the mouse is silent.
    state = session.state()
    assert (state.tutor.challenge_id, state.tutor.step_index, state.tutor.step_count) == (
        "setup",
        0,
        5,
    )
    assert state.circuit.status == "open"
    assert state.circuit.source_voltage == 6.0
    mat.touch(*BATTERY_WIRE)
    state = session.state()
    assert state.tutor.phase == "test"
    assert (state.probe.present, state.probe.pulse_hz, state.probe.buzz) == (True, 0.0, False)
    see_and_explain(session)

    # 1. Close the loop: predict, draw the missing line, feel a steady pulse.
    state = session.state()
    assert (state.tutor.challenge_id, state.tutor.phase) == ("close_the_loop", "predict")
    assert state.tutor.choices == ["yes", "no"]
    session.handle(Answer(choice="yes"))
    assert session.state().tutor.phase == "build"
    mat.draw("gap")
    state = session.state()
    assert (state.tutor.phase, state.circuit.status) == ("test", "closed")
    bulb_a = next(part for part in state.circuit.parts if part.id == "bulb_a")
    assert bulb_a.brightness == pytest.approx(1.0, abs=0.01)
    assert state.probe.pulse_hz == pytest.approx(3.0, abs=0.01)  # 0.6 A
    assert see_and_explain(session).tutor.correct is True

    # 2. Series: a wrong prediction, then both bulbs dim and the pulse halves everywhere.
    assert session.state().tutor.challenge_id == "series"
    session.handle(Answer(choice="no change"))
    mat.put("tile", "bulb")
    state = session.state()
    assert (state.tutor.phase, state.circuit.topology) == ("test", "series")
    bulbs = [part for part in state.circuit.parts if part.kind == "bulb"]
    assert [round(bulb.brightness, 2) for bulb in bulbs] == [0.25, 0.25]
    assert state.probe.pulse_hz == pytest.approx(1.5, abs=0.01)  # 0.3 A
    mat.touch(*BULB_A_WIRE)
    assert session.state().probe.pulse_hz == pytest.approx(1.5, abs=0.01)  # same everywhere
    explained = see_and_explain(session)
    assert explained.tutor.correct is False
    assert "two bulbs resist more than one" in explained.tutor.feedback

    # 3. Parallel: each bulb at full brightness, each branch at half the battery wire's rate.
    assert session.state().tutor.challenge_id == "parallel"
    session.handle(Answer(choice="both brighter"))
    mat.put("tile", "wire")
    mat.put("side", "bulb")
    state = session.state()
    assert (state.tutor.phase, state.circuit.topology) == ("test", "parallel")
    assert all(
        part.brightness == pytest.approx(1.0, abs=0.01)
        for part in state.circuit.parts
        if part.kind == "bulb"
    )
    assert state.probe.pulse_hz == pytest.approx(3.0, abs=0.01)  # bulb A's branch, 0.6 A
    mat.touch(*SIDE_WIRE)
    assert session.state().probe.pulse_hz == pytest.approx(3.0, abs=0.01)  # 0.6 A
    mat.touch(*BATTERY_WIRE)
    # 1.2 A. The wires' own tiny resistance takes a sliver off, so allow a little more.
    assert session.state().probe.pulse_hz == pytest.approx(6.0, abs=0.02)
    see_and_explain(session)

    # 4. Short: both bulbs go out, the shorted path buzzes, every other wire is silent.
    state = session.state()
    assert (state.tutor.challenge_id, state.tutor.phase) == ("short", "build")
    mat.draw("shortcut")
    mat.touch(*SHORTCUT)
    state = session.state()
    assert (state.tutor.phase, state.circuit.status) == ("test", "short")
    assert all(part.brightness == 0 for part in state.circuit.parts)
    assert (state.probe.buzz, state.probe.pulse_hz) == (True, 0.0)
    assert any(wire.overloaded for wire in state.circuit.wires)
    mat.touch(*BULB_A_WIRE)
    state = session.state()
    assert (state.probe.buzz, state.probe.pulse_hz) == (False, 0.0)
    see_and_explain(session)

    state = session.state()
    assert state.tutor.phase == "done"

    # What the database remembers: three predictions, five steps, mastery per concept.
    learner_id = platform.learners.get_or_create("Ada")
    attempts = platform.learners.attempts(learner_id)
    assert [(a.step_id, a.choice, a.correct) for a in attempts] == [
        ("close_the_loop", "yes", True),
        ("series", "no change", False),
        ("parallel", "both brighter", True),
    ]
    progress = platform.learners.load_progress(learner_id)
    assert progress.completed_steps == {
        "circuits-101": ["setup", "close_the_loop", "series", "parallel", "short"]
    }
    assert state.learner == {
        "closed_loop": "solid",
        "current": "solid",
        "voltage": "solid",
        "resistance": "shaky",
        "series": "shaky",
        "parallel": "solid",
    }


def test_progress_is_kept_between_sessions(platform):
    session, mat = start(platform)
    session.state()
    session.handle(Next())
    session.handle(Next())  # setup finished

    resumed, _ = start(platform)
    assert resumed.state().tutor.challenge_id == "close_the_loop"

    someone_else, _ = start(platform, nickname="Grace")
    assert someone_else.state().tutor.challenge_id == "setup"


def test_the_wheel_changes_the_voltage_within_limits(platform):
    session, mat = start(platform)
    mat.draw("gap")
    session.handle(Wheel(steps=2))
    state = session.state()
    assert state.circuit.source_voltage == 7.0
    assert state.circuit.total_current == pytest.approx(0.7, abs=0.01)
    session.handle(Wheel(steps=100))
    assert session.state().circuit.source_voltage == 9.0
    session.handle(Wheel(steps=-100))
    state = session.state()
    assert state.circuit.source_voltage == 0.0
    assert state.circuit.total_current == 0.0


def test_an_unchanged_mat_is_not_solved_again(platform, monkeypatch):
    import tacto.session as session_module

    calls = 0
    real = session_module.solve_circuit

    def counting(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(session_module, "solve_circuit", counting)
    session, mat = start(platform)
    for _ in range(30):
        session.state()
    assert calls == 1
    mat.draw("gap")
    session.state()
    session.handle(Wheel(steps=1))
    session.state()
    assert calls == 3


def test_an_unknown_lesson_is_refused_with_the_known_ones_listed():
    with pytest.raises(LookupError, match="circuits-101"):
        open_platform(database_url="sqlite://", lesson_id="chemistry-101")
