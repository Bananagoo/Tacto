from pathlib import Path

import pytest

from tacto.contract import Grid
from tacto.lab import Lab, MatView
from tacto.lesson import (
    SETTLE_SECONDS,
    DoneWhen,
    Lesson,
    LessonFileError,
    LessonRunner,
    arrangement_of,
    is_satisfied,
    load_lesson,
)
from tacto.pieces import solve_pieces
from tacto_mock.scenario import branch, loop

LESSON_FILE = Path(__file__).resolve().parents[2] / "lessons" / "circuits-101.yaml"
GRID = Grid(cols=9, rows=6)

CIRCUITS = {
    "empty": [],
    "open": loop(closed=False),
    "one_bulb": loop(closed=True),
    "series": loop(closed=True, bottom="bulb"),
    "parallel": loop(closed=True) + branch("bulb"),
    "short": loop(closed=True) + branch("wire"),
    "bypassed": loop(closed=True, bottom="bulb") + branch("wire"),
}


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.mark.parametrize(
    "name, expected",
    [
        ("empty", None),
        ("open", None),
        ("one_bulb", "single"),
        ("series", "series"),
        ("parallel", "parallel"),
        ("short", None),
        ("bypassed", "single"),  # the bulb with a wire across it is dark
    ],
)
def test_arrangement(name, expected):
    assert arrangement_of(*solve_pieces(CIRCUITS[name], 6.0)) == expected


def test_arrangement_holds_at_other_voltages():
    assert arrangement_of(*solve_pieces(CIRCUITS["series"], 2.0)) == "series"
    assert arrangement_of(*solve_pieces(CIRCUITS["parallel"], 9.0)) == "parallel"


def test_conditions_left_out_are_not_checked():
    solved = solve_pieces(CIRCUITS["series"], 6.0)
    assert is_satisfied(DoneWhen(status="working"), *solved)
    assert is_satisfied(DoneWhen(bulbs=2, lit_bulbs=2, batteries=1, arrangement="series"), *solved)
    assert not is_satisfied(DoneWhen(status="working", arrangement="parallel"), *solved)
    with pytest.raises(ValueError, match="at least one condition"):
        DoneWhen()


def test_the_lesson_file_loads_and_each_goal_is_reachable():
    lesson = load_lesson(LESSON_FILE)
    assert [step.id for step in lesson.steps] == [
        "setup",
        "close_the_loop",
        "series",
        "parallel",
        "short",
    ]
    reached_by = ["open", "one_bulb", "series", "parallel", "short"]
    for step, name in zip(lesson.steps, reached_by, strict=True):
        assert is_satisfied(step.done_when, *solve_pieces(CIRCUITS[name], 6.0)), step.id
    # No step is already finished by an empty mat, or by the step before it.
    for index, step in enumerate(lesson.steps):
        assert not is_satisfied(step.done_when, *solve_pieces([], 6.0)), step.id
        if index:
            before = solve_pieces(CIRCUITS[reached_by[index - 1]], 6.0)
            assert not is_satisfied(step.done_when, *before), step.id


def test_a_bad_lesson_file_names_the_file(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "id: x\ntitle: X\nsteps:\n  - id: a\n    prompt: hi\n    done_when: {statu: open}\n"
    )
    with pytest.raises(LessonFileError, match="bad.yaml"):
        load_lesson(bad)
    with pytest.raises(LessonFileError, match="cannot be read"):
        load_lesson(tmp_path / "missing.yaml")


def runner(clock: Clock) -> LessonRunner:
    return LessonRunner(load_lesson(LESSON_FILE), now=clock)


def test_a_step_is_done_only_after_the_goal_has_settled():
    clock = Clock()
    lesson = runner(clock)
    goal = solve_pieces(CIRCUITS["open"], 6.0)
    assert lesson.update(*solve_pieces([], 6.0)).step_done is False
    assert lesson.update(*goal).step_done is False
    clock.t = SETTLE_SECONDS - 0.1
    assert lesson.update(*goal).step_done is False
    clock.t = SETTLE_SECONDS
    report = lesson.update(*goal)
    assert (report.step_id, report.step_index, report.step_count) == ("setup", 0, 5)
    assert report.step_done is True and report.lesson_done is False


def test_a_goal_met_only_in_passing_does_not_count():
    clock = Clock()
    lesson = runner(clock)
    lesson.update(*solve_pieces(CIRCUITS["open"], 6.0))
    clock.t = 0.3
    lesson.update(*solve_pieces([], 6.0))  # the pieces were only passing through
    clock.t = 0.6
    assert lesson.update(*solve_pieces(CIRCUITS["open"], 6.0)).step_done is False


def test_done_stays_done_and_the_next_prompt_follows_after_the_linger():
    clock = Clock()
    lesson = runner(clock)
    goal = solve_pieces(CIRCUITS["open"], 6.0)
    lesson.update(*goal)
    clock.t = 0.5
    lesson.update(*goal)
    clock.t = 3.0
    assert lesson.update(*solve_pieces([], 6.0)).step_done is True  # still on show
    clock.t = 0.5 + 6.0
    report = lesson.update(*solve_pieces([], 6.0))
    assert (report.step_id, report.step_done) == ("close_the_loop", False)
    assert "Close the gap" in report.prompt


def test_the_whole_lesson_runs_to_the_end_and_restarts():
    clock = Clock()
    lesson = runner(clock)
    for name in ("open", "one_bulb", "series", "parallel", "short"):
        solved = solve_pieces(CIRCUITS[name], 6.0)
        lesson.update(*solved)
        clock.t += 0.5
        assert lesson.update(*solved).step_done is True, name
        clock.t += 6.0
    report = lesson.update(*solve_pieces(CIRCUITS["short"], 6.0))
    assert (report.step_id, report.step_done, report.lesson_done) == ("short", True, True)
    clock.t += 100
    assert lesson.update(*solve_pieces([], 6.0)).lesson_done is True
    lesson.restart()
    report = lesson.update(*solve_pieces([], 6.0))
    assert (report.step_index, report.step_done, report.lesson_done) == (0, False, False)


def test_step_ids_must_be_unique():
    step = {"id": "a", "prompt": "p", "done_when": {"status": "open"}}
    with pytest.raises(ValueError, match="unique"):
        Lesson(id="x", title="X", steps=[step, step])


# ---------- the lab carries the lesson ----------


class Mat:
    def __init__(self, placed, finger=None, mat_visible=True) -> None:
        self.current = MatView(tuple(placed), finger, mat_visible)

    def view(self) -> MatView:
        return self.current


SWITCH_XY = (4 / 8, 1.5 / 5)  # the middle of the switch from dot (4,1) to (4,2)


def test_the_lab_reports_the_lesson():
    clock = Clock()
    lab = Lab(GRID, Mat(CIRCUITS["open"]), source_name="manual", lesson=runner(clock), now=clock)
    assert lab.state().lesson.step_id == "setup"
    clock.t = 0.6
    assert lab.state().lesson.step_done is True
    lab.restart_lesson()
    assert lab.state().lesson.step_done is False


def test_without_a_lesson_the_lesson_fields_are_empty():
    assert Lab(GRID, Mat([]), source_name="manual").state().lesson.step_count == 0


def test_a_finger_resting_on_a_switch_changes_nothing():
    # Open and closed switches are different pieces; the learner swaps them.
    clock = Clock()
    lab = Lab(GRID, Mat(CIRCUITS["open"], finger=SWITCH_XY), source_name="camera", now=clock)
    for t in (0.0, 0.5, 1.0, 5.0):
        clock.t = t
        state = lab.state()
        assert state.circuit.status == "open"
        assert next(p for p in state.pieces if p.type == "switch").closed is False
