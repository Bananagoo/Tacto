"""A reflection as a funnel of questions: what the lesson file may hold, and what it may not."""

from pathlib import Path

import pytest
import yaml

from tacto.contract import Circuit
from tacto.lesson import (
    MAX_FUNNEL_LEVELS,
    DoneWhen,
    Funnel,
    Lesson,
    LessonFileError,
    is_satisfied,
    load_lesson,
)

LESSON_FILE = Path(__file__).resolve().parents[2] / "lessons" / "circuits-101.yaml"


def funnel(**changes) -> dict:
    """A small valid funnel, as the YAML gives it."""
    base = {
        "target_idea": "More voltage, more current.",
        "confirmation": "Yes, more current.",
        "misconceptions": [{"tag": "pulse_is_voltage", "description": "Pulse is the voltage."}],
        "levels": [
            {"question": "Why faster?", "correct_examples": ["more current", "more flow"]},
            {
                "question": "More or less?",
                "correct_examples": ["more", "more of it"],
                "confirmation": "More, exactly.",
            },
        ],
        "exit": {"line": "It is the current. Touch the bulb.", "then": [{"touching": "bulb"}]},
    }
    return base | changes


def lesson_with(reflection) -> dict:
    step = {"id": "a", "prompt": "p", "done_when": {"status": "working"}, "reflection": reflection}
    return {"id": "x", "title": "X", "steps": [step]}


def write(tmp_path: Path, content: dict) -> Path:
    path = tmp_path / "lesson.yaml"
    path.write_text(yaml.safe_dump(content))
    return path


# ---------- the demo lesson ----------


def test_the_demo_lesson_loads_with_a_funnel_on_each_reflecting_step():
    lesson = load_lesson(LESSON_FILE)
    funnels = {step.id: step.funnel for step in lesson.steps if step.funnel}
    assert list(funnels) == ["raise_voltage", "series", "parallel"]
    for step_id, loaded in funnels.items():
        assert len(loaded.levels) == MAX_FUNNEL_LEVELS, step_id
        assert len(loaded.misconceptions) == 2, step_id
        assert all(len(level.correct_examples) >= 2 for level in loaded.levels), step_id


def test_the_opening_question_is_still_the_steps_reflection():
    lesson = load_lesson(LESSON_FILE)
    by_id = {step.id: step for step in lesson.steps}
    assert (
        by_id["raise_voltage"].reflection_question
        == "Why did the pulse get faster when you raised the voltage?"
    )
    assert by_id["setup"].reflection_question is None and by_id["setup"].funnel is None


def test_the_voltage_exit_goes_down_to_three_volts_then_back_to_six():
    step = next(s for s in load_lesson(LESSON_FILE).steps if s.id == "raise_voltage")
    down, up = step.funnel.exit.then
    assert (down.touching, down.max_voltage, up.min_voltage) == ("bulb", 3, 6)
    assert step.funnel.exit.timeout_seconds == 20


def test_the_series_exit_asks_for_the_other_bulb_and_the_parallel_exit_for_bulb_then_battery():
    steps = {s.id: s for s in load_lesson(LESSON_FILE).steps}
    (other,) = steps["series"].funnel.exit.then
    assert other.touching == "bulb" and other.different_piece is True
    assert [goal.touching for goal in steps["parallel"].funnel.exit.then] == ["bulb", "battery"]


# ---------- what a funnel may hold ----------


def test_a_plain_question_is_still_a_reflection():
    step = Lesson.model_validate(lesson_with("Why?")).steps[0]
    assert step.reflection == "Why?" and step.funnel is None and step.reflection_question == "Why?"


def test_a_level_uses_its_own_confirmation_or_the_funnels():
    loaded = Funnel.model_validate(funnel())
    assert loaded.confirmation_at(0) == "Yes, more current."
    assert loaded.confirmation_at(1) == "More, exactly."


@pytest.mark.parametrize(
    "what, broken, names",
    [
        ("no levels", funnel(levels=[]), "levels"),
        (
            "four levels",
            funnel(levels=[{"question": "q", "correct_examples": ["a", "b"]}] * 4),
            "levels",
        ),
        (
            "one example answer",
            funnel(levels=[{"question": "q", "correct_examples": ["a"]}]),
            "correct_examples",
        ),
        (
            "an empty question",
            funnel(levels=[{"question": "", "correct_examples": ["a", "b"]}]),
            "question",
        ),
        ("no exit", {k: v for k, v in funnel().items() if k != "exit"}, "exit"),
        ("an exit with nothing to do", funnel(exit={"line": "x", "then": []}), "then"),
        (
            "an exit goal that is not a goal",
            funnel(exit={"line": "x", "then": [{"touching": "laser"}]}),
            "touching",
        ),
        (
            "a tag with spaces",
            funnel(misconceptions=[{"tag": "pulse is voltage", "description": "d"}]),
            "tag",
        ),
        (
            "the same tag twice",
            funnel(misconceptions=[{"tag": "t", "description": "d"}] * 2),
            "unique",
        ),
        ("a misspelt field", funnel(target_ideea="x"), "target_ideea"),
        (
            "no target idea",
            {k: v for k, v in funnel().items() if k != "target_idea"},
            "target_idea",
        ),
    ],
)
def test_a_malformed_funnel_fails_with_the_file_the_step_and_the_field(
    what, broken, names, tmp_path
):
    path = write(tmp_path, lesson_with(broken))
    with pytest.raises(LessonFileError) as raised:
        load_lesson(path)
    message = str(raised.value)
    assert "lesson.yaml" in message and "steps.0.reflection" in message, what
    assert names in message, what
    # The mistake is reported as a funnel's, not as "this should have been a string".
    assert "valid string" not in message or names == "question", what


# ---------- the new voltage condition ----------


@pytest.mark.parametrize("volts, met", [(2.5, True), (3.0, True), (3.5, False), (6.0, False)])
def test_max_voltage_is_met_at_or_below_it(volts, met):
    circuit = Circuit(status="working", voltage=volts)
    assert is_satisfied(DoneWhen(max_voltage=3), [], circuit) is met


def test_min_and_max_voltage_together_make_a_range():
    wanted = DoneWhen(min_voltage=3, max_voltage=6)
    for volts, met in [(2.5, False), (3, True), (4.5, True), (6, True), (6.5, False)]:
        assert is_satisfied(wanted, [], Circuit(status="working", voltage=volts)) is met
