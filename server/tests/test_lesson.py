from pathlib import Path

import pytest

from tacto.contract import ContinueLesson, Grid, SetMode, SetVoltage, Touch
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
from tacto_mock.scenario import BATTERY, BULB_A, SWITCH, branch, loop

LESSON_FILE = Path(__file__).resolve().parents[2] / "lessons" / "circuits-101-full.yaml"
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

# One action per step; the next goal must not already hold after the previous one.
ACTIONS = [
    ("open", 3.0, None),
    ("one_bulb", 3.0, None),
    ("one_bulb", 3.0, BULB_A),
    ("one_bulb", 6.0, BULB_A),
    ("series", 6.0, BULB_A),
    ("parallel", 6.0, BATTERY),
]


def observation(action):
    name, volts, piece_id = action
    return (
        *solve_pieces(CIRCUITS[name], volts),
        Touch(present=piece_id is not None, piece_id=piece_id),
    )


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
        "feel_current",
        "raise_voltage",
        "series",
        "parallel",
    ]
    for step, action in zip(lesson.steps, ACTIONS, strict=True):
        assert is_satisfied(step.done_when, *observation(action)), step.id
    # No step is already finished by an empty mat, or by the step before it.
    for index, step in enumerate(lesson.steps):
        assert not is_satisfied(step.done_when, *solve_pieces([], 6.0)), step.id
        if index:
            before = observation(ACTIONS[index - 1])
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
    assert (report.step_id, report.step_index, report.step_count) == ("setup", 0, 6)
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
    assert "Swap in the closed switch" in report.prompt


def test_the_whole_lesson_runs_to_the_end_and_restarts():
    clock = Clock()
    lesson = runner(clock)
    for action in ACTIONS:
        solved = observation(action)
        lesson.update(*solved)
        clock.t += 0.5
        assert lesson.update(*solved).step_done is True, action
        lesson.continue_step(lesson.update(*solved).step_id)
        clock.t += 6.0
    report = lesson.update(*observation(ACTIONS[-1]))
    assert (report.step_id, report.step_done, report.lesson_done) == ("parallel", True, True)
    clock.t += 100
    assert lesson.update(*solve_pieces([], 6.0)).lesson_done is True
    lesson.restart()
    report = lesson.update(*solve_pieces([], 6.0))
    assert (report.step_index, report.step_done, report.lesson_done) == (0, False, False)


def test_open_switch_goal_needs_an_actual_open_switch():
    goal = DoneWhen(switch_closed=False)
    assert is_satisfied(goal, *solve_pieces(CIRCUITS["open"], 3))
    assert not is_satisfied(goal, *solve_pieces([], 3))
    assert not is_satisfied(goal, *solve_pieces(CIRCUITS["one_bulb"], 3))
    missing = [p for p in CIRCUITS["open"] if p.type != "switch"]
    assert not is_satisfied(goal, *solve_pieces(missing, 3))


@pytest.mark.parametrize("piece_id", [None, SWITCH, "missing"])
def test_touch_goal_requires_the_requested_piece(piece_id):
    assert not is_satisfied(DoneWhen(touching="bulb"), *observation(("one_bulb", 3, piece_id)))


@pytest.mark.parametrize("name, volts", [("open", 3), ("one_bulb", 0), ("short", 6)])
def test_touch_requires_a_piece_carrying_current(name, volts):
    assert not is_satisfied(DoneWhen(touching="current"), *observation((name, volts, BULB_A)))


def test_touch_requires_a_present_finger_and_accepts_negative_battery_current():
    solved = solve_pieces(CIRCUITS["parallel"], 6)
    goal = DoneWhen(touching="battery")
    assert not is_satisfied(goal, *solved, Touch(present=False, piece_id=BATTERY))
    assert is_satisfied(goal, *solved, Touch(present=True, piece_id=BATTERY))
    assert is_satisfied(DoneWhen(touching="current"), *observation(("one_bulb", 3, SWITCH)))


def test_voltage_target_does_not_skip_the_touch():
    goal = DoneWhen(min_voltage=6, touching="bulb")
    assert not is_satisfied(goal, *observation(("one_bulb", 5.5, BULB_A)))
    assert not is_satisfied(goal, *observation(("one_bulb", 6, None)))
    assert is_satisfied(goal, *observation(("one_bulb", 6, BULB_A)))


def test_losing_the_mat_resets_the_settle_timer():
    clock = Clock()
    lesson = runner(clock)
    goal = observation(ACTIONS[0])
    lesson.update(*goal)
    clock.t = 0.4
    assert not lesson.update(*goal, mat_visible=False).step_done
    clock.t = 1
    assert not lesson.update(*goal).step_done
    clock.t = 1.5
    assert lesson.update(*goal).step_done


def test_a_brief_touch_does_not_finish_a_step():
    clock = Clock()
    lesson = LessonRunner(
        Lesson(
            id="touch",
            title="Touch",
            steps=[{"id": "touch", "prompt": "Touch", "done_when": {"touching": "bulb"}}],
        ),
        now=clock,
    )
    goal = observation(ACTIONS[2])
    lesson.update(*goal)
    clock.t = 0.4
    lesson.update(*goal[:2])
    clock.t = 1
    assert not lesson.update(*goal).step_done
    clock.t = 1.5
    assert lesson.update(*goal).step_done


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
    lab.handle(SetMode(mode="lab"))
    assert lab.state().lesson.step_id == "setup"
    clock.t = 0.6
    assert lab.state().lesson.step_done is True
    lab.restart_lesson()
    assert lab.state().lesson.step_done is False


def test_tinker_is_open_ended_and_entering_lab_resets_voltage_and_progress():
    clock = Clock()
    lab = Lab(GRID, Mat(CIRCUITS["open"]), source_name="manual", lesson=runner(clock), now=clock)
    assert lab.state().mode == "tinker"
    lab.handle(SetVoltage(volts=8))
    clock.t = 100
    assert lab.state().lesson.step_count == 0
    lab.handle(SetMode(mode="lab"))
    assert lab.state().circuit.voltage == 3
    assert lab.state().lesson.step_index == 0
    clock.t += 1
    assert lab.state().lesson.step_done
    lab.handle(SetVoltage(volts=6))
    lab.handle(SetMode(mode="tinker"))
    clock.t += 100
    assert lab.state().circuit.voltage == 6
    assert lab.state().lesson.step_count == 0
    lab.handle(SetMode(mode="lab"))
    state = lab.state()
    assert state.circuit.voltage == 3
    assert state.lesson.step_index == 0 and not state.lesson.step_done


def test_lab_reflection_waits_for_continue_and_rejects_stale_or_early_clicks():
    clock = Clock()
    lesson = runner(clock)
    for action in ACTIONS[:4]:
        goal = observation(action)
        lesson.update(*goal)
        clock.t += 0.5
        report = lesson.update(*goal)
        assert report.step_done
        clock.t += 6
    report = lesson.update(*goal)
    assert report.step_id == "raise_voltage" and report.reflection
    clock.t += 100
    assert lesson.update(*goal).step_id == "raise_voltage"
    lesson.continue_step("wrong_step")
    assert lesson.update(*goal).step_id == "raise_voltage"
    lesson.continue_step("raise_voltage")
    report = lesson.update(*goal)
    assert report.step_id == "series" and not report.step_done and report.reflection is None
    lesson.continue_step("raise_voltage")
    lesson.continue_step("series")  # the action has not been completed yet
    assert lesson.update(*goal).step_id == "series"


def test_lab_passes_fingertip_to_lesson_and_finishes_only_after_final_reflection():
    clock = Clock()
    mat = Mat([])
    lab = Lab(GRID, mat, source_name="manual", lesson=runner(clock), now=clock)
    lab.handle(SetMode(mode="lab"))
    for name, volts, piece_id in ACTIONS:
        placed = CIRCUITS[name]
        piece = next((p for p in placed if p.id == piece_id), None)
        finger = (
            None
            if piece is None
            else ((piece.a[0] + piece.b[0]) / 16, (piece.a[1] + piece.b[1]) / 10)
        )
        mat.current = MatView(tuple(placed), finger)
        lab.handle(SetVoltage(volts=volts))
        lab.state()
        clock.t += 0.5
        state = lab.state()
        assert state.lesson.step_done
        if state.lesson.reflection:
            assert not state.lesson.lesson_done
            lab.handle(ContinueLesson(step_id=state.lesson.step_id))
        clock.t += 6
    assert lab.state().lesson.lesson_done
    lab.restart_lesson()
    state = lab.state()
    assert state.circuit.voltage == 3 and state.lesson.step_index == 0
    assert not state.lesson.step_done and not state.lesson.lesson_done
    assert state.lesson.reflection is None


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
