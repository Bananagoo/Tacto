"""The short demo lesson (lessons/circuits-101.yaml): three steps, one spoken question."""

from pathlib import Path

import pytest

from tacto.contract import Touch
from tacto.grader import Grade  # noqa: F401  (the funnel's labels are the grader's)
from tacto.lesson import CONFIRM_SECONDS, LessonRunner, is_satisfied, load_lesson
from tacto.pieces import solve_pieces
from tacto_mock.scenario import BATTERY, BULB_A, branch, loop

LESSON = load_lesson(Path(__file__).resolve().parents[2] / "lessons" / "circuits-101.yaml")

# The starting layout: the loop with the open switch in it, and an empty side branch.
START = loop(closed=False) + [p for p in branch("bulb") if p.type == "wire"]
CLOSED = loop(closed=True) + [p for p in branch("bulb") if p.type == "wire"]
PARALLEL = loop(closed=True) + branch("bulb")


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
