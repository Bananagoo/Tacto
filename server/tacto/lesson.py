"""Lesson steps for the lab: a fixed sequence, each step finished by the circuit itself.

A lesson is data (`lessons/<id>.yaml`): each step has a prompt to show and the
circuit and touch conditions that complete it. Spoken reflections wait for Continue;
answers are not recorded or scored and there are no timers on the learner.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    ValidationError,
    model_validator,
)

from tacto.contract import MAX_VOLTS, Circuit, CircuitStatus, LessonStep, Piece, PieceType, Touch
from tacto.sim.feel import MIN_CURRENT_AMPS

Arrangement = Literal["single", "series", "parallel"]

# A bulb this dim looks off on screen, so it does not count as lit.
LIT_THRESHOLD = 0.02
# The goal must hold this long before the step counts, so a circuit that only passes
# through the goal while pieces are being moved does not finish the step.
SETTLE_SECONDS = 0.5
# Two currents within this fraction of each other are "the same" (wires have a tiny resistance).
SAME_CURRENT = 0.02


class _Strict(BaseModel):
    # A typo in a lesson file should fail loudly at load time, not be ignored.
    model_config = ConfigDict(extra="forbid")


class DoneWhen(_Strict):
    """Conditions on the circuit and fingertip. Every condition given must hold."""

    status: CircuitStatus | None = None
    batteries: int | None = Field(None, ge=0)
    bulbs: int | None = Field(None, ge=0)
    lit_bulbs: int | None = Field(None, ge=0)
    arrangement: Arrangement | None = None
    switch_closed: bool | None = None
    min_voltage: float | None = Field(None, ge=0, le=MAX_VOLTS)
    max_voltage: float | None = Field(None, ge=0, le=MAX_VOLTS)
    # A piece type, or any piece carrying current. Touch goals always require current.
    touching: PieceType | Literal["current"] | None = None

    @model_validator(mode="after")
    def _has_a_condition(self) -> DoneWhen:
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("done_when needs at least one condition")
        return self


# ---------- a reflection as a funnel of narrowing questions ----------
# The lab asks an open "why" question. An answer that misses gets a narrower question,
# then a choice between two options, then the lab states the idea and asks for an action
# on the mat. Every line the lab says is written in the lesson file; nothing is generated.

_Line = Annotated[str, Field(min_length=1)]
MAX_FUNNEL_LEVELS = 3


class Misconception(_Strict):
    """A wrong idea worth naming when an answer shows it."""

    tag: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: _Line


class FunnelLevel(_Strict):
    """One question, and what a right answer to it sounds like."""

    question: _Line
    # Two or three answers that should be graded correct, said the way a learner would.
    correct_examples: list[_Line] = Field(min_length=2, max_length=5)
    # Said when this level is answered correctly; the funnel's own is used when left out.
    confirmation: _Line | None = None


class ExitGoal(DoneWhen):
    """One thing to do on the mat once the lab has stated the idea."""

    # The touched piece must not be the one the learner was touching when the step was
    # finished: "touch the other bulb".
    different_piece: bool = False


class FunnelExit(_Strict):
    """What happens when no answer landed: the lab says the idea and asks for an action."""

    line: _Line
    # Goals to meet one after another, in this order.
    then: list[ExitGoal] = Field(min_length=1)
    # The lesson moves on after this long whether or not the action was done.
    timeout_seconds: float = Field(20.0, gt=0)


class Funnel(_Strict):
    # What the learner should come to say, in one sentence. The grader is given this.
    target_idea: _Line
    confirmation: _Line
    misconceptions: list[Misconception] = []
    levels: list[FunnelLevel] = Field(min_length=1, max_length=MAX_FUNNEL_LEVELS)
    exit: FunnelExit

    @model_validator(mode="after")
    def _tags_are_unique(self) -> Funnel:
        tags = [misconception.tag for misconception in self.misconceptions]
        if len(set(tags)) != len(tags):
            raise ValueError("misconception tags must be unique within a reflection")
        return self

    def confirmation_at(self, level: int) -> str:
        return self.levels[level].confirmation or self.confirmation


def _reflection_kind(value: Any) -> str:
    # Chosen by shape, so a mistake inside a funnel is reported as that mistake and not
    # as "this is not a string".
    return "funnel" if isinstance(value, dict | Funnel) else "question"


Reflection = Annotated[
    Annotated[_Line, Tag("question")] | Annotated[Funnel, Tag("funnel")],
    Discriminator(_reflection_kind),
]


class Step(_Strict):
    id: str
    prompt: str = Field(min_length=1)
    # One question to answer out loud, or a funnel of them. Either waits for the learner.
    reflection: Reflection | None = None
    done_when: DoneWhen
    linger_seconds: float | None = Field(None, ge=0)  # overrides the lesson's

    @property
    def funnel(self) -> Funnel | None:
        return self.reflection if isinstance(self.reflection, Funnel) else None

    @property
    def reflection_question(self) -> str | None:
        """The question the reflection opens with."""
        if isinstance(self.reflection, Funnel):
            return self.reflection.levels[0].question
        return self.reflection


class Lesson(_Strict):
    id: str
    title: str
    linger_seconds: float = Field(6.0, ge=0)
    steps: list[Step] = Field(min_length=1)

    @model_validator(mode="after")
    def _step_ids_are_unique(self) -> Lesson:
        ids = [step.id for step in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError("step ids must be unique")
        return self


class LessonFileError(ValueError):
    """A lesson file could not be read or is not a valid lesson."""


def load_lesson(path: Path) -> Lesson:
    """The lesson in one YAML file. Errors name the file: these are edited by hand."""
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise LessonFileError(f"{path}: cannot be read: {error}") from error
    except yaml.YAMLError as error:
        raise LessonFileError(f"{path}: is not valid YAML: {error}") from error
    try:
        return Lesson.model_validate(content)
    except ValidationError as error:
        raise LessonFileError(f"{path}: is not a valid lesson: {error}") from error


def arrangement_of(pieces: Sequence[Piece], circuit: Circuit) -> Arrangement | None:
    """How the lit bulbs are connected, judged from the solved currents.

    In series every lit bulb carries the whole battery current. In parallel the
    bulbs' currents add up to it. Anything else (or no lit bulb) is None.
    """
    currents = [abs(p.current) for p in _lit_bulbs(pieces)]
    total = circuit.total_current
    if not currents or total <= 0:
        return None
    if len(currents) == 1:
        return "single"
    if all(math.isclose(current, total, rel_tol=SAME_CURRENT) for current in currents):
        return "series"
    if math.isclose(sum(currents), total, rel_tol=SAME_CURRENT):
        return "parallel"
    return None


def is_satisfied(
    done_when: DoneWhen,
    pieces: Sequence[Piece],
    circuit: Circuit,
    touch: Touch | None = None,
) -> bool:
    """True when every condition the step gives holds. Conditions left out are not checked."""
    wanted_and_found = (
        (done_when.status, circuit.status),
        (done_when.batteries, sum(p.type == "battery" for p in pieces)),
        (done_when.bulbs, sum(p.type == "bulb" for p in pieces)),
        (done_when.lit_bulbs, len(_lit_bulbs(pieces))),
        (done_when.arrangement, arrangement_of(pieces, circuit)),
    )
    if not all(wanted is None or wanted == found for wanted, found in wanted_and_found):
        return False
    if done_when.switch_closed is not None:
        switches = [p for p in pieces if p.type == "switch"]
        if not switches or any(p.closed is not done_when.switch_closed for p in switches):
            return False
    if done_when.min_voltage is not None and circuit.voltage < done_when.min_voltage:
        return False
    if done_when.max_voltage is not None and circuit.voltage > done_when.max_voltage:
        return False
    if done_when.touching is not None:
        if touch is None or not touch.present:
            return False
        piece = next((p for p in pieces if p.id == touch.piece_id), None)
        if piece is None or piece.shorted or abs(piece.current) < MIN_CURRENT_AMPS:
            return False
        if done_when.touching != "current" and piece.type != done_when.touching:
            return False
    return True


def _lit_bulbs(pieces: Sequence[Piece]) -> list[Piece]:
    return [p for p in pieces if p.type == "bulb" and (p.brightness or 0) > LIT_THRESHOLD]


class LessonRunner:
    """Walks one learner through a lesson's steps as the circuit changes.

    A step is done once its goal has held for `SETTLE_SECONDS`, and stays done even if
    the learner then changes the mat. After the linger time the next prompt appears,
    except a reflection waits for Continue. The last reflection ends the lesson.
    """

    def __init__(self, lesson: Lesson, *, now: Callable[[], float] = time.monotonic) -> None:
        self._lesson = lesson
        self._now = now
        self.restart()

    def restart(self) -> None:
        self._index = 0
        self._met_since: float | None = None
        self._done_at: float | None = None
        self._continued = False

    def continue_step(self, step_id: str) -> None:
        """Acknowledge a spoken reflection; late clicks cannot skip another step."""
        step = self._lesson.steps[self._index]
        if step.id != step_id or step.reflection is None or self._done_at is None:
            return
        if self._index == len(self._lesson.steps) - 1:
            self._continued = True
        else:
            self._index += 1
            self._met_since = self._done_at = None

    def update(
        self,
        pieces: Sequence[Piece],
        circuit: Circuit,
        touch: Touch | None = None,
        *,
        mat_visible: bool = True,
    ) -> LessonStep:
        """Take in the latest solved circuit and report where the lesson stands."""
        now = self._now()
        step = self._lesson.steps[self._index]
        last = self._index == len(self._lesson.steps) - 1
        if self._done_at is None:
            if not mat_visible or not is_satisfied(step.done_when, pieces, circuit, touch):
                self._met_since = None
            elif self._met_since is None:
                self._met_since = now
            elif now - self._met_since >= SETTLE_SECONDS:
                self._done_at = now
        elif not last and step.reflection is None and now - self._done_at >= self._linger(step):
            self._index += 1
            self._met_since = self._done_at = None
            # The circuit that finished the last step may already meet the next goal.
            return self.update(pieces, circuit, touch, mat_visible=mat_visible)
        return LessonStep(
            lesson_id=self._lesson.id,
            step_id=step.id,
            step_index=self._index,
            step_count=len(self._lesson.steps),
            prompt=step.prompt,
            step_done=self._done_at is not None,
            lesson_done=(
                last and self._done_at is not None and (step.reflection is None or self._continued)
            ),
            reflection=step.reflection_question
            if self._done_at is not None and not self._continued
            else None,
        )

    def _linger(self, step: Step) -> float:
        if step.linger_seconds is not None:
            return step.linger_seconds
        return self._lesson.linger_seconds
