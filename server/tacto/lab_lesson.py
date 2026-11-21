"""Lesson steps for the lab: a fixed sequence, each step finished by the circuit itself.

A lesson is data (`lessons/lab/<id>.yaml`): each step has a prompt to show and the
circuit conditions that complete it. There are no predictions to score, no hints and
no timers on the learner; a prompt may still ask "what do you expect?" as wording.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from tacto.contract_v2 import Circuit, CircuitStatus, LessonStep, Piece

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
    """Conditions on the solved circuit. Every condition given must hold."""

    status: CircuitStatus | None = None
    batteries: int | None = Field(None, ge=0)
    bulbs: int | None = Field(None, ge=0)
    lit_bulbs: int | None = Field(None, ge=0)
    arrangement: Arrangement | None = None

    @model_validator(mode="after")
    def _has_a_condition(self) -> DoneWhen:
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("done_when needs at least one condition")
        return self


class Step(_Strict):
    id: str
    prompt: str = Field(min_length=1)
    done_when: DoneWhen
    linger_seconds: float | None = Field(None, ge=0)  # overrides the lesson's


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


def is_satisfied(done_when: DoneWhen, pieces: Sequence[Piece], circuit: Circuit) -> bool:
    """True when every condition the step gives holds. Conditions left out are not checked."""
    wanted_and_found = (
        (done_when.status, circuit.status),
        (done_when.batteries, sum(p.type == "battery" for p in pieces)),
        (done_when.bulbs, sum(p.type == "bulb" for p in pieces)),
        (done_when.lit_bulbs, len(_lit_bulbs(pieces))),
        (done_when.arrangement, arrangement_of(pieces, circuit)),
    )
    return all(wanted is None or wanted == found for wanted, found in wanted_and_found)


def _lit_bulbs(pieces: Sequence[Piece]) -> list[Piece]:
    return [p for p in pieces if p.type == "bulb" and (p.brightness or 0) > LIT_THRESHOLD]


class LessonRunner:
    """Walks one learner through a lesson's steps as the circuit changes.

    A step is done once its goal has held for `SETTLE_SECONDS`, and stays done even if
    the learner then changes the mat. After the step's linger time the next step's
    prompt appears. The last step, once done, ends the lesson.
    """

    def __init__(self, lesson: Lesson, *, now: Callable[[], float] = time.monotonic) -> None:
        self._lesson = lesson
        self._now = now
        self.restart()

    def restart(self) -> None:
        self._index = 0
        self._met_since: float | None = None
        self._done_at: float | None = None

    def update(self, pieces: Sequence[Piece], circuit: Circuit) -> LessonStep:
        """Take in the latest solved circuit and report where the lesson stands."""
        now = self._now()
        step = self._lesson.steps[self._index]
        last = self._index == len(self._lesson.steps) - 1
        if self._done_at is None:
            if not is_satisfied(step.done_when, pieces, circuit):
                self._met_since = None
            elif self._met_since is None:
                self._met_since = now
            elif now - self._met_since >= SETTLE_SECONDS:
                self._done_at = now
        elif not last and now - self._done_at >= self._linger(step):
            self._index += 1
            self._met_since = self._done_at = None
            # The circuit that finished the last step may already meet the next goal.
            return self.update(pieces, circuit)
        return LessonStep(
            lesson_id=self._lesson.id,
            step_id=step.id,
            step_index=self._index,
            step_count=len(self._lesson.steps),
            prompt=step.prompt,
            step_done=self._done_at is not None,
            lesson_done=last and self._done_at is not None,
        )

    def _linger(self, step: Step) -> float:
        if step.linger_seconds is not None:
            return step.linger_seconds
        return self._lesson.linger_seconds
