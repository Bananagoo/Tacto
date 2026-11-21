"""A lesson file with a mistake in it must be rejected when it is loaded."""

import pytest
from pydantic import ValidationError

from tacto.lessons.models import Lesson


def lesson(**changes) -> dict:
    step = {
        "id": "series",
        "teaches": ["current"],
        "predict": {
            "say": "What will the first bulb do?",
            "choices": {"dimmer": ["dimmer"], "same": ["same"], "brighter": ["brighter"]},
            "answer": "dimmer",
            "misconceptions": {"same": "Feel the pulse: it slowed down."},
        },
        "build": {"say": "Add a second bulb.", "done_when": {"bulbs": 2, "topology": "series"}},
        "observe": {"say": "Slide your finger along the loop."},
        "explain": {"say": "The current is the same all the way round."},
        "hints": ["Is there a gap anywhere?"],
    }
    step.update(changes.pop("step", {}))
    data = {
        "id": "circuits-101",
        "title": "Circuits",
        "concepts": [
            {"id": "closed_loop", "title": "Closed loop"},
            {"id": "current", "title": "Current", "requires": ["closed_loop"]},
        ],
        "steps": [step],
    }
    data.update(changes)
    return data


def test_a_well_formed_lesson_loads():
    loaded = Lesson.model_validate(lesson())
    assert loaded.steps[0].predict.answer == "dimmer"
    assert loaded.steps[0].build.done_when.topology == "series"


def test_a_step_may_have_no_prediction():
    assert Lesson.model_validate(lesson(step={"predict": None})).steps[0].predict is None


@pytest.mark.parametrize(
    "bad",
    [
        {"step": {"teaches": ["magnetism"]}},  # unknown concept
        {"step": {"predict": {"say": "?", "choices": {"a": [], "b": []}, "answer": "c"}}},
        {
            "step": {
                "predict": {
                    "say": "?",
                    "choices": {"a": [], "b": []},
                    "answer": "a",
                    "misconceptions": {"a": "no"},
                }
            }
        },
        {"step": {"build": {"say": "Build.", "done_when": {}}}},  # no condition at all
        {"step": {"build": {"say": "Build.", "done_when": {"bulbz": 2}}}},  # typo in a key
        {"concepts": [{"id": "current", "title": "Current", "requires": ["nothing"]}]},
        {"steps": []},
    ],
)
def test_mistakes_are_rejected(bad):
    with pytest.raises(ValidationError):
        Lesson.model_validate(lesson(**bad))
