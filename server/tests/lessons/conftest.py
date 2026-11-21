"""A small lesson, circuits that do and do not finish its steps, and a clock to drive the engine."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from tacto.contract import Circuit, Part, Wire
from tacto.lessons.models import Lesson

# Not a round time, so a test would notice if anything truncated or replaced it.
START = datetime(2026, 11, 21, 10, 0, 0, 123456, tzinfo=UTC)

CLOSE_THE_LOOP = {
    "id": "close_the_loop",
    "teaches": ["closed_loop"],
    "build": {"say": "Draw the missing wire.", "done_when": {"status": "closed", "lit_bulbs": 1}},
    "observe": {"say": "Rest a finger on any wire."},
    "explain": {"say": "Current flows only in a closed loop."},
    "hints": ["Is there a gap anywhere?", "Follow the wire from the battery with your finger."],
}
SERIES = {
    "id": "series",
    "teaches": ["current", "series"],
    "predict": {
        "say": "What will the first bulb do?",
        "choices": {"dimmer": ["dimmer", "darker"], "same": ["same"], "brighter": ["brighter"]},
        "answer": "dimmer",
        "misconceptions": {"same": "Feel the pulse: it slowed down, so less current flows."},
    },
    "build": {
        "say": "Place the second bulb on the wire.",
        "done_when": {"status": "closed", "bulbs": 2, "topology": "series"},
    },
    "observe": {"say": "Slide your finger along the loop."},
    "explain": {"say": "The current is the same all the way round."},
    "hints": ["Where could a second bulb go?", "Lay it over a wire.", "Try the top wire."],
}
CONCEPTS = [
    {"id": "closed_loop", "title": "Closed loop"},
    {"id": "current", "title": "Current", "requires": ["closed_loop"]},
    {"id": "series", "title": "Series", "requires": ["current"]},
]


def make_lesson(*steps: dict) -> Lesson:
    return Lesson.model_validate(
        {"id": "mini", "title": "Mini", "concepts": CONCEPTS, "steps": list(steps)}
    )


@pytest.fixture
def lesson() -> Lesson:
    """Two steps: the first has no prediction, the second has one."""
    return make_lesson(CLOSE_THE_LOOP, SERIES)


@pytest.fixture
def prediction_lesson() -> Lesson:
    """A single step with a prediction and no hints."""
    return make_lesson({**SERIES, "hints": []})


@pytest.fixture
def two_prediction_lesson() -> Lesson:
    """Two steps that ask for a prediction about the same concepts."""
    return make_lesson(SERIES, {**SERIES, "id": "series_again"})


@pytest.fixture
def at() -> Callable[[float], datetime]:
    """Time is whatever the test says it is: `at(30)` is 30 s after the start."""
    return lambda seconds: START + timedelta(seconds=seconds)


BATTERY = Part(id="battery", kind="battery", a=(0, 4), b=(2, 4))


def _bulb(part_id: str, col: int, brightness: float) -> Part:
    return Part(id=part_id, kind="bulb", a=(col, 0), b=(col + 1, 0), brightness=brightness)


@pytest.fixture
def open_loop() -> Circuit:
    """A battery and a bulb with a gap in the wiring. Finishes neither step."""
    return Circuit(
        status="open", parts=[BATTERY, _bulb("bulb_a", 0, 0.0)], wires=[Wire(a=(0, 0), b=(0, 4))]
    )


@pytest.fixture
def one_bulb() -> Circuit:
    """One lit bulb in a closed loop. Finishes `close_the_loop` only."""
    return Circuit(
        status="closed",
        topology="single",
        source_voltage=3.0,
        total_current=0.3,
        parts=[BATTERY, _bulb("bulb_a", 0, 1.0)],
        wires=[Wire(a=(0, 0), b=(0, 4), current=0.3), Wire(a=(1, 0), b=(2, 4), current=0.3)],
    )


@pytest.fixture
def two_in_series() -> Circuit:
    """Two dim bulbs in one loop. Finishes `series`, and `close_the_loop` does not want it."""
    return Circuit(
        status="closed",
        topology="series",
        source_voltage=3.0,
        total_current=0.15,
        parts=[BATTERY, _bulb("bulb_a", 0, 0.25), _bulb("bulb_b", 3, 0.25)],
        wires=[Wire(a=(0, 0), b=(0, 4), current=0.15), Wire(a=(4, 0), b=(2, 4), current=0.15)],
    )
