"""One learner's loop: look at the mat, solve the circuit, advance the lesson, report State.

This is where the product's parts meet, through plain data: a Source reports the mat and
the fingertip, the mat layout turns that into parts and wires, the simulation solves
them, and the lesson engine decides what the tutor says. Nothing here touches the
network. The database is written only when the lesson reports an event.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from .contract import (
    Answer,
    Circuit,
    ClientMessage,
    Next,
    Part,
    Probe,
    State,
    Wheel,
    Wire,
)
from .learner.graph import mastery_map
from .learner.models import Attempt
from .lessons.engine import LessonEngine
from .lessons.events import LessonEvent, PredictionMade, StepCompleted
from .lessons.models import Lesson
from .mat.compose import compose
from .mat.locate import element_at
from .mat.models import MatLayout, MatReading
from .observation import Fingertip, Source
from .sim import probe_for, solve_circuit
from .sim.feel import wire_id
from .store.repositories import LearnerRepository

VOLTS_PER_WHEEL_STEP = 0.5
MAX_SOURCE_VOLTS = 9.0

Clock = Callable[[], datetime]
SourceName = str


def utc_now() -> datetime:
    return datetime.now(UTC)


class Session:
    """Implements `tacto.world.World` for one learner working through one lesson."""

    def __init__(
        self,
        *,
        lesson: Lesson,
        layout: MatLayout,
        source: Source,
        source_name: SourceName,
        learner_id: int,
        learners: LearnerRepository,
        clock: Clock = utc_now,
    ) -> None:
        self._layout = layout
        self._source = source
        self._source_name = source_name
        self._learner_id = learner_id
        self._learners = learners
        self._clock = clock
        self._lesson_id = lesson.id
        self._concept_ids = [concept.id for concept in lesson.concepts]
        self._engine = LessonEngine(lesson, learners.load_progress(learner_id), now=clock())
        self._source_voltage = layout.battery_volts
        # The last solve, reused while neither the mat nor the voltage has changed.
        self._solved_for: tuple[MatReading, float] | None = None
        self._circuit = Circuit()

    def state(self) -> State:
        now = self._clock()
        observation = self._source.observe()
        circuit = self._solve(observation.reading)
        self._engine.on_circuit(circuit, now=now)
        self._engine.on_tick(now=now)
        self._save(self._engine.drain_events())
        return State(
            t=now.timestamp(),
            source=self._source_name,
            circuit=circuit,
            probe=_probe(circuit, self._layout, observation.fingertip),
            tutor=self._engine.tutor(),
            learner=mastery_map(self._engine.progress, self._concept_ids),
        )

    def handle(self, message: ClientMessage) -> None:
        now = self._clock()
        if isinstance(message, Wheel):
            volts = self._source_voltage + message.steps * VOLTS_PER_WHEEL_STEP
            self._source_voltage = min(MAX_SOURCE_VOLTS, max(0.0, volts))
        elif isinstance(message, Answer):
            self._engine.on_answer(message.choice, now=now)
        elif isinstance(message, Next):
            self._engine.on_next(now=now)
        # CalibrateTouch belongs to the camera source and is handled there.
        self._save(self._engine.drain_events())

    def _solve(self, reading: MatReading) -> Circuit:
        key = (reading, self._source_voltage)
        if key != self._solved_for:
            parts, wires = compose(self._layout, reading)
            self._circuit = solve_circuit(parts, wires, self._source_voltage)
            self._solved_for = key
        return self._circuit

    def _save(self, events: Sequence[LessonEvent]) -> None:
        for event in events:
            if isinstance(event, PredictionMade):
                self._learners.record_attempt(
                    self._learner_id,
                    Attempt(
                        lesson_id=self._lesson_id,
                        step_id=event.step_id,
                        choice=event.choice,
                        correct=event.correct,
                        at=event.at,
                    ),
                )
            elif isinstance(event, StepCompleted):
                self._learners.save_progress(self._learner_id, self._engine.progress)


def _probe(circuit: Circuit, layout: MatLayout, fingertip: Fingertip | None) -> Probe:
    if fingertip is None:
        return Probe()
    touched = element_at(
        circuit.parts,
        circuit.wires,
        cols=layout.cols,
        rows=layout.rows,
        x=fingertip.x,
        y=fingertip.y,
    )
    return probe_for(circuit, present=True, x=fingertip.x, y=fingertip.y, on=_element_id(touched))


def _element_id(element: Part | Wire | None) -> str | None:
    if element is None:
        return None
    return element.id if isinstance(element, Part) else wire_id(element.a, element.b)
