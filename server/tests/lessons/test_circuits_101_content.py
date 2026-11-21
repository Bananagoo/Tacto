"""The Circuits 101 lesson file obeys the rules for spoken lines in `.claude/rules/lessons.md`.

These checks run on the real file, so an edit to the wording that breaks a rule fails here
and not in front of a learner.
"""

import re
from pathlib import Path

import pytest

from tacto.lessons.loader import load_lesson
from tacto.lessons.models import Lesson, Step

LESSON_FILE = Path(__file__).resolve().parents[3] / "lessons" / "circuits-101.yaml"

MAX_WORDS = 19  # "under 20 words"
SENTENCE_END = ".?!"
# A number with a unit letter straight after it ("6V", "6 V", "20mA") reads badly aloud.
NUMBER_WITH_UNIT = re.compile(r"\d\s?[A-Za-zΩµ]")
SYMBOLS_READ_BADLY = ("Ω", "=", "/")
VIBRATION_WORDS = re.compile(r"\b(vibrat\w*|buzz\w*|puls\w*)\b", re.IGNORECASE)
WHEEL_WORDS = re.compile(r"\b(wheel|scroll\w*)\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def lesson() -> Lesson:
    return load_lesson(LESSON_FILE)


def spoken_lines(step: Step) -> list[str]:
    lines = [step.build.say, step.observe.say, step.explain.say, *step.hints]
    if step.predict is not None:
        lines += [step.predict.say, *step.predict.misconceptions.values()]
    return lines


def all_spoken_lines(lesson: Lesson) -> list[str]:
    return [line for step in lesson.steps for line in spoken_lines(step)]


def contains_word(line: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", line, re.IGNORECASE) is not None


def test_the_lesson_has_the_five_stages_in_order(lesson):
    assert lesson.id == "circuits-101"
    assert [step.id for step in lesson.steps] == [
        "setup",
        "close_the_loop",
        "series",
        "parallel",
        "short",
    ]


def test_the_concept_graph_matches_the_plan(lesson):
    assert {concept.id: concept.requires for concept in lesson.concepts} == {
        "closed_loop": [],
        "current": ["closed_loop"],
        "voltage": ["closed_loop"],
        "resistance": ["current"],
        "series": ["current", "resistance"],
        "parallel": ["current", "voltage"],
    }


def test_every_concept_is_taught_by_some_step(lesson):
    taught = {concept for step in lesson.steps for concept in step.teaches}
    assert taught == {concept.id for concept in lesson.concepts}


def test_each_step_is_done_when_the_plan_says(lesson):
    done_when = {
        step.id: step.build.done_when.model_dump(exclude_none=True) for step in lesson.steps
    }
    assert done_when == {
        "setup": {"status": "open", "bulbs": 1},
        "close_the_loop": {"status": "closed", "lit_bulbs": 1},
        "series": {"topology": "series", "lit_bulbs": 2},
        "parallel": {"topology": "parallel", "lit_bulbs": 2},
        "short": {"status": "short"},
    }


def test_only_the_middle_three_steps_ask_for_a_prediction(lesson):
    asks = [step.id for step in lesson.steps if step.predict is not None]
    assert asks == ["close_the_loop", "series", "parallel"]


def test_every_spoken_line_is_one_sentence(lesson):
    for line in all_spoken_lines(lesson):
        assert line == line.strip() and line, repr(line)
        assert line[-1] in SENTENCE_END, f"does not end like a sentence: {line!r}"
        assert not any(mark in line[:-1] for mark in SENTENCE_END), f"more than one: {line!r}"


def test_every_spoken_line_is_under_twenty_words(lesson):
    for line in all_spoken_lines(lesson):
        assert len(line.split()) <= MAX_WORDS, f"{len(line.split())} words: {line!r}"


def test_no_spoken_line_has_units_or_symbols_that_read_badly_aloud(lesson):
    for line in all_spoken_lines(lesson):
        assert not NUMBER_WITH_UNIT.search(line), f"number with a unit: {line!r}"
        assert not any(symbol in line for symbol in SYMBOLS_READ_BADLY), repr(line)


def test_spoken_lines_address_the_learner_directly(lesson):
    # Second person: the tutor says "you", never "the learner", "I" or "we".
    for line in all_spoken_lines(lesson):
        for word in ("learner", "student", "user", "I", "we", "us", "let's"):
            assert not contains_word(line, word), f"not second person: {line!r}"


def test_vibration_is_never_called_voltage_and_the_wheel_is_never_called_current(lesson):
    for line in all_spoken_lines(lesson):
        if VIBRATION_WORDS.search(line):
            assert not contains_word(line, "voltage"), f"vibration is current: {line!r}"
        if WHEEL_WORDS.search(line):
            assert not contains_word(line, "current"), f"the wheel is voltage: {line!r}"


def test_every_prediction_has_two_to_four_choices_and_a_misconception(lesson):
    for step in lesson.steps:
        if step.predict is None:
            continue
        assert 2 <= len(step.predict.choices) <= 4, step.id
        assert len(step.predict.misconceptions) >= 1, step.id
        for choice, keywords in step.predict.choices.items():
            assert keywords, f"{step.id}: choice {choice!r} has no spoken keywords"


def test_the_known_wrong_ideas_from_the_design_are_answered(lesson):
    steps = {step.id: step for step in lesson.steps}
    # Series: "the first bulb uses up the current" and "nothing changes".
    assert len(steps["series"].predict.misconceptions) == 2
    # Parallel: "both get dimmer because the current splits".
    assert any("split" in line for line in steps["parallel"].predict.misconceptions.values())


def test_spoken_keywords_belong_to_one_choice_only(lesson):
    # Keywords are matched before any model is asked, so one word must not mean two choices.
    for step in lesson.steps:
        if step.predict is None:
            continue
        keywords = [word.lower() for words in step.predict.choices.values() for word in words]
        assert len(keywords) == len(set(keywords)), step.id
        assert all(isinstance(word, str) for word in keywords), step.id


def test_every_step_has_a_ladder_of_three_hints(lesson):
    for step in lesson.steps:
        assert len(step.hints) == 3, step.id
        assert len(set(step.hints)) == 3, step.id


def test_no_hint_states_the_answer_to_its_prediction(lesson):
    for step in lesson.steps:
        if step.predict is None:
            continue
        answer = step.predict.answer
        # The answer as shown on screen, and every way of saying it.
        answer_words = {answer, *step.predict.choices[answer]}
        for hint in step.hints:
            for word in answer_words:
                assert not contains_word(hint, word), f"{step.id}: {hint!r} says {word!r}"
