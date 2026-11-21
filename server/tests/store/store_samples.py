"""Small valid lessons for the store tests to save and read back."""

from tacto.lessons.models import Lesson


def make_step(step_id: str, teaches: list[str]) -> dict:
    return {
        "id": step_id,
        "teaches": teaches,
        "predict": {
            "say": "What will the bulb do?",
            "choices": {"dimmer": ["dimmer", "darker"], "same": ["same"]},
            "answer": "dimmer",
            "misconceptions": {"same": "The pulse slowed, so less current flows."},
        },
        "build": {"say": "Add a bulb.", "done_when": {"topology": "series", "lit_bulbs": 2}},
        "observe": {"say": "Slide a finger along the loop."},
        "explain": {"say": "The current is the same all the way round."},
        "hints": ["A smaller question?", "Look here.", "Try it on your loop."],
    }


def make_lesson(lesson_id: str = "circuits-101", **changes: object) -> Lesson:
    """A small valid lesson; pass fields to override."""
    data: dict = {
        "id": lesson_id,
        "title": "Circuits",
        "concepts": [
            {"id": "closed_loop", "title": "Closed loop"},
            {"id": "current", "title": "Current", "requires": ["closed_loop"]},
            {"id": "series", "title": "Series", "requires": ["current", "closed_loop"]},
        ],
        "steps": [make_step("close_the_loop", ["closed_loop"]), make_step("series", ["series"])],
    }
    data.update(changes)
    return Lesson.model_validate(data)
