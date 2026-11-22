"""The short demo lesson (lessons/circuits-101.yaml): three steps, one spoken question."""

from pathlib import Path

import pytest

from tacto.contract import Touch, segment_id
from tacto.grader import Grade  # noqa: F401  (the funnel's labels are the grader's)
from tacto.lesson import CONFIRM_SECONDS, LessonRunner, is_satisfied, load_lesson
from tacto.pieces import Placed, solve_pieces
from tacto_mock.scenario import BATTERY, BULB_A, loop

LESSON = load_lesson(Path(__file__).resolve().parents[2] / "lessons" / "circuits-101.yaml")

# The starting layout: the loop with the open switch in it, and a side branch with a gap for
# the second bulb. One branch wire is a resistor (Katie, 22 Nov 2026), so the second bulb
# glows dimmer than the first and the meter has a resistor to read.
SIDE = [Placed("resistor", (2, 1), (2, 2)), Placed("wire", (3, 2), (3, 1))]
SECOND_BULB = Placed("bulb", (2, 2), (3, 2))
START = loop(closed=False) + SIDE
CLOSED = loop(closed=True) + SIDE
PARALLEL = CLOSED + [SECOND_BULB]
RESISTOR = segment_id((2, 1), (2, 2))
BULB_B = segment_id((2, 2), (3, 2))


def seen(placed, volts, piece_id=None):
    return (
        *solve_pieces(placed, volts),
        Touch(present=piece_id is not None, piece_id=piece_id),
    )


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_three_steps_and_one_question():
    assert [step.id for step in LESSON.steps] == ["close_the_loop", "raise_voltage", "parallel"]
    assert [step.id for step in LESSON.steps if step.reflection] == ["raise_voltage"]
    assert LESSON.linger_seconds == 2.5
    assert LESSON.steps[1].funnel.exit.timeout_seconds == 12


def test_the_starting_layout_finishes_nothing():
    for step in LESSON.steps:
        assert not is_satisfied(step.done_when, *seen(START, 3.0)), step.id


@pytest.mark.parametrize(
    "step_id, done, not_yet",
    [
        ("close_the_loop", (CLOSED, 3.0, None), (START, 3.0, None)),
        ("raise_voltage", (CLOSED, 6.0, BULB_A), (CLOSED, 3.0, BULB_A)),
        ("parallel", (PARALLEL, 6.0, BATTERY), (CLOSED, 6.0, BATTERY)),
    ],
)
def test_each_goal_is_met_by_its_action_and_not_by_the_step_before(step_id, done, not_yet):
    step = next(s for s in LESSON.steps if s.id == step_id)
    assert is_satisfied(step.done_when, *seen(*done))
    assert not is_satisfied(step.done_when, *seen(*not_yet))


def test_a_quick_run_from_start_to_finish():
    clock = Clock()
    runner = LessonRunner(LESSON, now=clock, adaptive=True)

    def hold(action, seconds=0.6):
        runner.update(*seen(*action))
        clock.t += seconds
        return runner.update(*seen(*action))

    assert hold((START, 3.0)).step_id == "close_the_loop"
    assert hold((CLOSED, 3.0)).step_done
    clock.t += LESSON.linger_seconds + 0.1
    state = hold((CLOSED, 6.0, BULB_A))
    assert (state.step_id, state.reflection_status) == ("raise_voltage", "asking")
    ticket = runner.begin_answer("raise_voltage", "more push so more flow")
    runner.finish_answer(ticket, "correct")
    runner.update(*seen(CLOSED, 6.0, BULB_A))  # the lab looks 15 times a second
    clock.t += CONFIRM_SECONDS + 0.1
    assert runner.update(*seen(CLOSED, 6.0, BULB_A)).step_id == "parallel"
    state = hold((PARALLEL, 6.0, BATTERY))
    assert state.lesson_done


def test_the_exit_time_limit_counts_from_when_its_line_has_been_said():
    clock = Clock()
    runner = LessonRunner(LESSON, now=clock, adaptive=True)
    runner.jump_to_reflection("raise_voltage")
    for _ in range(3):
        ticket = runner.begin_answer("raise_voltage", "no idea")
        runner.finish_answer(ticket, "incorrect")
    state = runner.update(*seen(CLOSED, 6.0, BULB_A))
    assert state.reflection_status == "exit"
    # No audio: the line counts as said after CONFIRM_SECONDS, then 12 s more.
    clock.t += CONFIRM_SECONDS + 11.5
    assert runner.update(*seen(CLOSED, 6.0, BULB_A)).step_id == "raise_voltage"
    clock.t += 1.0
    assert runner.update(*seen(CLOSED, 6.0, BULB_A)).step_id == "parallel"


def test_a_spoken_exit_line_gets_its_full_twelve_seconds_after_it_ends():
    clock = Clock()
    runner = LessonRunner(LESSON, now=clock, adaptive=True, audio_for=lambda line: "/voice/x.wav")
    runner.jump_to_reflection("raise_voltage")
    for _ in range(3):
        ticket = runner.begin_answer("raise_voltage", "no idea")
        runner.finish_answer(ticket, "incorrect")
    state = runner.update(*seen(CLOSED, 6.0, BULB_A))
    clock.t += 9.0  # the line takes about 9 s to say
    runner.line_heard("raise_voltage", state.reflection_line_id)
    clock.t += 11.5
    assert runner.update(*seen(CLOSED, 6.0, BULB_A)).step_id == "raise_voltage"
    clock.t += 1.0
    assert runner.update(*seen(CLOSED, 6.0, BULB_A)).step_id == "parallel"


def test_the_resistor_in_the_branch_leaves_steps_one_and_two_alone_and_dims_the_second_bulb():
    # Hand-worked, at 6 V. Before step 3 the branch is open: one bulb, 10 ohms, 0.6 A. After,
    # the second branch is bulb + resistor, 20 ohms, 0.3 A; the battery carries 0.6 + 0.3.
    pieces, circuit = solve_pieces(CLOSED, 6.0)
    by_id = {piece.id: piece for piece in pieces}
    assert by_id[BULB_A].current == pytest.approx(0.6, abs=1e-3)
    assert by_id[RESISTOR].current == pytest.approx(0.0, abs=1e-3)

    pieces, circuit = solve_pieces(PARALLEL, 6.0)
    by_id = {piece.id: piece for piece in pieces}
    # 0.899: the wires' own 0.001 ohm each, eight of them shared, take a little.
    assert circuit.total_current == pytest.approx(0.9, abs=2e-3)
    assert abs(by_id[BULB_A].current) == pytest.approx(0.6, abs=1e-3)
    assert abs(by_id[BULB_B].current) == pytest.approx(0.3, abs=1e-3)
    assert abs(by_id[RESISTOR].current) == pytest.approx(0.3, abs=1e-3)
    assert abs(by_id[RESISTOR].voltage) == pytest.approx(3.0, abs=1e-2)
    assert by_id[BULB_B].brightness < by_id[BULB_A].brightness


def test_the_meter_gets_ohms_for_bulbs_and_resistors_and_they_fit_ohms_law():
    pieces, _ = solve_pieces(PARALLEL, 6.0)
    by_id = {piece.id: piece for piece in pieces}
    for piece_id in (BULB_A, BULB_B, RESISTOR):
        piece = by_id[piece_id]
        assert piece.resistance == 10.0
        assert abs(piece.voltage) == pytest.approx(abs(piece.current) * 10.0, abs=1e-2)
    assert by_id[BATTERY].resistance is None
    # Like a real meter (22 Nov 2026): a wire and a closed switch read 0 ohms; an open switch
    # has no number (the meter shows OL, open line).
    assert all(p.resistance == 0.0 for p in pieces if p.type == "wire")
    assert all(p.resistance == 0.0 for p in pieces if p.type == "switch")  # closed here
    opened, _ = solve_pieces(START, 6.0)
    assert next(p for p in opened if p.type == "switch").resistance is None
