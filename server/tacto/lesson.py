"""Lesson steps for the lab: a fixed sequence, each step finished by the circuit itself.

A lesson is data (`lessons/<id>.yaml`): each step has a prompt to show and the
circuit and touch conditions that complete it. Spoken reflections wait for Continue;
answers are not recorded or scored and there are no timers on the learner.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
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

from tacto import funnel as funnel_rules
from tacto.contract import MAX_VOLTS, Circuit, CircuitStatus, LessonStep, Piece, PieceType, Touch
from tacto.sim.feel import MIN_CURRENT_AMPS

Arrangement = Literal["single", "series", "parallel"]

# A bulb this dim looks off on screen, so it does not count as lit.
LIT_THRESHOLD = 0.02
# The goal must hold this long before the step counts, so a circuit that only passes
# through the goal while pieces are being moved does not finish the step.
SETTLE_SECONDS = 0.5
# After a right answer the confirmation stays up this long, to be read or heard, before
# the next step's prompt replaces it.
# TODO(Katie): tune once the lines are spoken; the longest confirmation takes about 5 s to say.
CONFIRM_SECONDS = 3.0
# When the confirmation is spoken the lesson waits for the browser to say it has finished,
# then this much longer, so the next prompt does not land on the last word ...
AFTER_HEARD_SECONDS = 0.6
# ... and no longer than this if the browser never says so (the longest line is about 6 s).
CONFIRM_MAX_SECONDS = 12.0
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

    @model_validator(mode="after")
    def _asks_for_something(self) -> ExitGoal:
        # An empty goal is always met, and would end the exit as soon as it began.
        conditions = self.model_dump(exclude={"different_piece"})
        if all(value is None for value in conditions.values()):
            raise ValueError("an exit goal needs at least one condition")
        if self.different_piece and self.touching is None:
            raise ValueError("different_piece needs `touching`: a different piece of what?")
        return self


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


def circuit_summary(pieces: Sequence[Piece], circuit: Circuit) -> str:
    """The mat in a line of plain words, for whoever grades an answer about it."""
    batteries = sum(p.type == "battery" for p in pieces)
    bulbs = sum(p.type == "bulb" for p in pieces)
    arrangement = arrangement_of(pieces, circuit)
    how = f", in {arrangement}" if arrangement in ("series", "parallel") else ""
    return (
        f"{'One battery' if batteries == 1 else f'{batteries} batteries'} at "
        f"{circuit.voltage:g} V. {bulbs} bulb{'' if bulbs == 1 else 's'}, "
        f"{len(_lit_bulbs(pieces))} lit{how}. {circuit.total_current:.2f} A at the battery. "
        f"The circuit is {circuit.status}."
    )


@dataclass(frozen=True)
class AnswerTicket:
    """One answer on its way to being graded: what was asked, and proof it is still current."""

    step_id: str
    funnel: Funnel
    level: int
    transcript: str
    attempt: int


class LessonRunner:
    """Walks one learner through a lesson's steps as the circuit changes.

    A step is done once its goal has held for `SETTLE_SECONDS`, and stays done even if
    the learner then changes the mat. After the linger time the next prompt appears,
    except a reflection waits: for Continue, or, when `adaptive`, for the funnel of
    questions to be answered (`funnel.py`). The last reflection ends the lesson.
    """

    def __init__(
        self,
        lesson: Lesson,
        *,
        now: Callable[[], float] = time.monotonic,
        adaptive: bool = False,
        audio_for: Callable[[str], str | None] | None = None,
    ) -> None:
        self._lesson = lesson
        self._now = now
        # Where a line's speech can be fetched, or None for a line that is only shown.
        self._audio_for = audio_for or (lambda line: None)
        # False: a reflection is one question on screen and Continue, whatever the lesson
        # file holds. True: a step with a funnel asks, takes answers and narrows.
        self._adaptive = adaptive
        self._attempt = 0
        self.restart()

    def restart(self) -> None:
        self._index = 0
        self._met_since: float | None = None
        self._done_at: float | None = None
        self._continued = False
        self._clear_reflection()

    def _clear_reflection(self) -> None:
        self._asking: funnel_rules.FunnelState | None = None
        self._line: str | None = None
        self._line_id = 0
        self._transcript: str | None = None
        self._thinking = False
        self._touched_when_done: str | None = None
        self._goal_since: float | None = None
        self._resolved_at: float | None = None
        self._heard_at: float | None = None
        self._exit_clock_started = False
        # Any answer still being graded belongs to a question that is no longer asked.
        self._attempt += 1

    def _say(self, line: str | None) -> None:
        if line is not None:
            self._line = line
            self._line_id += 1
            self._heard_at = None

    def line_heard(self, step_id: str, line_id: int) -> None:
        """The browser finished playing the line being said now. Others are ignored."""
        if (
            self._asking is not None
            and self._lesson.steps[self._index].id == step_id
            and line_id == self._line_id
        ):
            self._heard_at = self._now()

    def _advance(self) -> None:
        if self._index == len(self._lesson.steps) - 1:
            self._continued = True
        else:
            self._index += 1
            self._met_since = self._done_at = None
        self._clear_reflection()

    def continue_step(self, step_id: str) -> None:
        """Move on from a reflection, skipping what is left of it; late clicks cannot skip
        another step."""
        step = self._lesson.steps[self._index]
        if step.id != step_id or step.reflection is None or self._done_at is None:
            return
        if not self._continued:
            self._advance()

    # ---------- answers ----------

    def jump_to_reflection(self, step_id: str) -> bool:
        """Go straight to a step's reflection as if the step had just been finished, for
        trying the questions without building the circuit. False for a step without one."""
        for index, step in enumerate(self._lesson.steps):
            if step.id == step_id and step.reflection is not None:
                self._index = index
                self._met_since = None
                self._done_at = self._now()
                self._continued = False
                self._clear_reflection()
                if self._adaptive and step.funnel is not None:
                    self._asking, line = funnel_rules.start(step.funnel)
                    self._say(line)
                return True
        return False

    def begin_answer(
        self, step_id: str, text: str, line_id: int | None = None
    ) -> AnswerTicket | None:
        """Take an answer to the question being asked. None when no answer is wanted now:
        another step, no question up, one already being graded, the exit, or an answer to
        a line the lab is no longer on."""
        step = self._lesson.steps[self._index]
        asking = self._asking
        if (
            step.id != step_id
            or (line_id is not None and line_id != self._line_id)
            or step.funnel is None
            or asking is None
            or asking.status != "asking"
            or self._thinking
        ):
            return None
        self._transcript = " ".join(text.split())
        self._thinking = True
        self._attempt += 1
        return AnswerTicket(step_id, step.funnel, asking.level, self._transcript, self._attempt)

    def finish_answer(self, ticket: AnswerTicket, label: str) -> None:
        """Take the grade of an answer. Dropped if the question has since gone."""
        if ticket.attempt != self._attempt or not self._thinking or self._asking is None:
            return
        self._thinking = False
        self._asking, line = funnel_rules.answer(ticket.funnel, self._asking, label, self._now())
        self._say(line)

    # ---------- the mat ----------

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
                if self._adaptive and step.funnel is not None:
                    self._touched_when_done = touch.piece_id if touch else None
                    self._asking, line = funnel_rules.start(step.funnel)
                    self._say(line)
        elif self._asking is not None and step.funnel is not None:
            if self._run_reflection(step.funnel, pieces, circuit, touch, mat_visible, now):
                # The mat that finished the exit may already meet the next step's goal.
                return self.update(pieces, circuit, touch, mat_visible=mat_visible)
        elif not last and step.reflection is None and now - self._done_at >= self._linger(step):
            self._index += 1
            self._met_since = self._done_at = None
            # The circuit that finished the last step may already meet the next goal.
            return self.update(pieces, circuit, touch, mat_visible=mat_visible)
        reflecting = self._done_at is not None and not self._continued
        asking = self._asking if reflecting else None
        question = step.reflection_question
        if asking is not None and step.funnel is not None:
            question = step.funnel.levels[asking.level].question
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
            reflection=question if reflecting else None,
            reflection_level=asking.level if asking else None,
            reflection_status=("thinking" if self._thinking else asking.status) if asking else None,
            reflection_line=self._line if asking else None,
            reflection_line_id=self._line_id if asking else 0,
            reflection_transcript=self._transcript if asking else None,
            reflection_audio=(
                self._audio_for(self._line) if asking and self._line is not None else None
            ),
        )

    def _run_reflection(
        self,
        asked: Funnel,
        pieces: Sequence[Piece],
        circuit: Circuit,
        touch: Touch | None,
        mat_visible: bool,
        now: float,
    ) -> bool:
        """One look at the mat while a reflection is up. True when the lesson moved on."""
        state = self._asking
        assert state is not None
        if state.status == "exit":
            # The exit's goals and its time limit both start once its line has been said:
            # a learner who missed three times gets to hear the idea, and the whole limit.
            if not self._exit_clock_started:
                began = state.exit_started_s if state.exit_started_s is not None else now
                said = self._said_by(began)
                if now < said:
                    return False
                # From here on the exit's clock runs from the moment the line was said.
                self._exit_clock_started = True
                self._asking = state = replace(state, exit_started_s=said)
            goal = asked.exit.then[state.exit_goal]
            met = mat_visible and is_satisfied(goal, pieces, circuit, touch)
            if met and goal.different_piece:
                met = touch is not None and touch.piece_id not in (None, self._touched_when_done)
            if not met:
                self._goal_since = None
            elif self._goal_since is None:
                self._goal_since = now
            # Held, like a step's own goal, so a hand passing over does not count. And not
            # before the idea has been stated: a finger already resting on the right piece
            # must not end the exit while the lab is still saying why.
            held = self._goal_since is not None and now - self._goal_since >= SETTLE_SECONDS
            after, _ = funnel_rules.on_mat(asked, state, goal_met=held, now=now)
            if after.exit_goal != state.exit_goal:
                self._goal_since = None
            self._asking = state = after
        if state.status != "resolved":
            return False
        if self._resolved_at is None:
            self._resolved_at = now
        # A right answer's confirmation stays up a moment. The exit has already said its
        # piece and been acted on, or timed out: nothing to wait for.
        if state.outcome == "correct":
            until = self._said_by(self._resolved_at)
            if self._heard_at is not None:
                until = max(until, self._heard_at + AFTER_HEARD_SECONDS)
            if now < until:
                return False
        self._advance()
        return True

    def _said_by(self, began: float) -> float:
        """When the line that began at `began` can be taken as said and taken in.

        Heard: once the browser reports it, but never sooner than the time to read it
        (the report also comes when the sound could not be played). Spoken but not yet
        reported: the longest a line takes. Only shown: the time to read it.
        """
        if self._heard_at is not None:
            return max(self._heard_at, began + CONFIRM_SECONDS)
        if self._line is not None and self._audio_for(self._line) is not None:
            return began + CONFIRM_MAX_SECONDS
        return began + CONFIRM_SECONDS

    def _linger(self, step: Step) -> float:
        if step.linger_seconds is not None:
            return step.linger_seconds
        return self._lesson.linger_seconds
