"""The lesson engine: walks a learner through any lesson, one step and one phase at a time.

Each step runs predict (if it has one) -> build -> test -> explain, and the lesson ends
at done. The engine is pure logic. It is fed what happened (the solved circuit, an answer,
"next", the time) and asked what the tutor should show; it never reads a clock, a file,
the network or a database. What it has to report comes out through `drain_events`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..contract import Circuit, Phase, Tutor
from ..learner.mastery import apply_step_result
from ..learner.models import Progress
from ..learner.zone import ZoneTracker
from .conditions import is_satisfied
from .events import LessonCompleted, LessonEvent, PredictionMade, StepCompleted
from .matching import match_choice
from .models import Lesson, Step

# How long the mat may sit unchanged during a build before the learner gets the next hint.
# TODO(lesson owner): a product choice; confirm with real learners at the desk.
IDLE_SECONDS = 30.0

# Where every part and wire sits, without the electrical values the solver adds.
_Layout = tuple[frozenset[tuple], frozenset[frozenset]]


class LessonEngine:
    """One learner's position in one lesson."""

    def __init__(self, lesson: Lesson, progress: Progress, *, now: datetime) -> None:
        self._lesson = lesson
        # A private copy: the caller's value must neither change under them nor move us.
        self._progress = progress.model_copy(deep=True)
        self._zone = ZoneTracker()
        self._events: list[LessonEvent] = []
        self._layout: _Layout | None = None

        # A finished lesson rests on its last step, which is where `done` reads its line.
        self._step_index = len(lesson.steps) - 1
        self._phase: Phase = "done"
        self._choice: str | None = None  # the learner's prediction for the current step
        self._hints_shown = 0
        self._idle_since = now

        completed = progress.completed_steps.get(lesson.id, [])
        for index, step in enumerate(lesson.steps):
            if step.id not in completed:
                self._start_step(index, now)
                break

    def on_circuit(self, circuit: Circuit, *, now: datetime) -> None:
        """The latest solved circuit. Called for every camera frame, so it must stay cheap."""
        layout = _layout_of(circuit)
        changed = layout != self._layout
        self._layout = layout
        if self._phase != "build":
            return
        if is_satisfied(self._step.build.done_when, circuit):
            self._phase = "test"
        elif changed:
            # The learner is working on it, so the wait for a hint starts over.
            self._idle_since = now

    def on_answer(self, text: str, *, now: datetime) -> None:
        """Something the learner said or clicked as their prediction."""
        predict = self._step.predict
        # Leaving `predict` on the first accepted answer is also what makes a voice
        # answer and a button press arriving together count once.
        if self._phase != "predict" or predict is None:
            return
        choice = match_choice(text, predict.choices)
        if choice is None:
            return
        self._choice = choice
        correct = choice == predict.answer
        if correct:
            self._zone.record_correct()
        elif self._has_been_wrong_before():
            self._zone.record_repeated_error()
        self._events.append(
            PredictionMade(step_id=self._step.id, choice=choice, correct=correct, at=now)
        )
        self._start_build(now)

    def on_next(self, *, now: datetime) -> None:
        """The learner asked to move on. Only the test and explain phases wait for this."""
        if self._phase == "test":
            self._phase = "explain"
        elif self._phase == "explain":
            self._complete_step(now)

    def on_tick(self, *, now: datetime) -> None:
        """Time has passed. Each idle period during a build is one step down the hint ladder."""
        if self._phase != "build":
            return
        period = timedelta(seconds=IDLE_SECONDS)
        # A loop, so periods are counted correctly however rarely the caller ticks.
        while now - self._idle_since >= period:
            self._idle_since += period
            self._hints_shown = min(self._hints_shown + 1, len(self._step.hints))
            self._zone.record_idle()

    def tutor(self) -> Tutor:
        """What the tutor panel should show right now."""
        step = self._step
        predict = step.predict
        return Tutor(
            lesson_id=self._lesson.id,
            challenge_id=step.id,
            step_index=self._step_index,
            step_count=len(self._lesson.steps),
            phase=self._phase,
            prompt=_prompt(step, self._phase),
            choices=list(predict.choices) if predict and self._phase == "predict" else [],
            correct=self._correct,
            feedback=self._feedback(),
            hint=self._hint(),
            zone=self._zone.zone,
            score=self._zone.score,
        )

    def drain_events(self) -> list[LessonEvent]:
        """What happened since the last call, oldest first. Each event is handed out once."""
        events, self._events = self._events, []
        return events

    @property
    def progress(self) -> Progress:
        """The learner's progress, updated each time a step completes."""
        return self._progress

    @property
    def _step(self) -> Step:
        return self._lesson.steps[self._step_index]

    @property
    def _correct(self) -> bool | None:
        predict = self._step.predict
        if predict is None or self._choice is None:
            return None
        return self._choice == predict.answer

    def _feedback(self) -> str:
        # Only with the explanation: the learner must see their prediction fail on the
        # mat before being told what was wrong with it.
        predict = self._step.predict
        if self._phase != "explain" or predict is None or self._choice is None:
            return ""
        return predict.misconceptions.get(self._choice, "")

    def _hint(self) -> str:
        if self._phase != "build" or self._hints_shown == 0:
            return ""
        return self._step.hints[self._hints_shown - 1]

    def _has_been_wrong_before(self) -> bool:
        concepts = self._progress.concepts
        return any(
            concepts[concept_id].wrong > 0
            for concept_id in self._step.teaches
            if concept_id in concepts
        )

    def _start_step(self, index: int, now: datetime) -> None:
        self._step_index = index
        self._choice = None
        if self._step.predict is not None:
            self._phase = "predict"
        else:
            self._start_build(now)

    def _start_build(self, now: datetime) -> None:
        # Never straight on to `test`, even if the mat already shows the goal: the phase
        # is left only by `on_circuit`, so the learner always gets the build line first.
        self._phase = "build"
        self._hints_shown = 0
        self._idle_since = now

    def _complete_step(self, now: datetime) -> None:
        step = self._step
        correct = self._correct
        self._progress = apply_step_result(
            self._progress, self._lesson.id, step.id, step.teaches, correct
        )
        self._events.append(
            StepCompleted(step_id=step.id, teaches=list(step.teaches), correct=correct, at=now)
        )
        next_index = self._step_index + 1
        if next_index < len(self._lesson.steps):
            self._start_step(next_index, now)
        else:
            self._events.append(LessonCompleted(lesson_id=self._lesson.id, at=now))
            self._phase = "done"
            self._choice = None


def _prompt(step: Step, phase: Phase) -> str:
    """The line the tutor says in each phase of a step."""
    match phase:
        case "predict":
            return step.predict.say if step.predict else ""
        case "build":
            return step.build.say
        case "test":
            return step.observe.say
        case "explain" | "done":
            return step.explain.say


def _layout_of(circuit: Circuit) -> _Layout:
    """What the learner's hands put on the mat, so two layouts differ only when they acted.

    Currents, voltages and brightness are left out because the wheel changes them
    without anyone touching the mat. Sets, so the order the camera lists things in and
    the direction a wire happens to be read in do not look like activity.
    """
    parts = frozenset((part.kind, part.a, part.b, part.closed) for part in circuit.parts)
    wires = frozenset(frozenset((wire.a, wire.b)) for wire in circuit.wires)
    return parts, wires
