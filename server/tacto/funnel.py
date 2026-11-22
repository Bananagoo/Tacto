"""The reflection funnel as a state machine: no clock, no network, no lesson file.

A reflection asks an open question. An answer that misses moves down to a narrower
question, then to a choice of two; after that the lab states the idea itself and asks
for an action on the mat. This module only says what happens next and which prewritten
line is spoken. Someone else grades the answers, watches the mat and keeps the time.

    correct              -> speak the confirmation, finished
    partial, incorrect   -> down one level; past the last level, to the exit
    unclear              -> the same question once more; a second time counts as partial
    exit                 -> finished when its goals are met in order, or when it times out

So a reflection grades at most one answer per level and cannot loop
(docs/voice-reflections-plan.md).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # the lesson runner imports this module; it only needs the type here
    from tacto.lesson import Funnel

Label = Literal["correct", "partial", "incorrect", "unclear"]
Status = Literal["asking", "exit", "resolved"]
Outcome = Literal["correct", "exit_done", "exit_timeout"]


@dataclass(frozen=True)
class FunnelState:
    status: Status = "asking"
    level: int = 0  # which question is being asked, or was answered correctly
    repeated: bool = False  # this question has already been asked a second time
    graded: int = 0  # answers that counted: every one but a first "unclear"
    exit_goal: int = 0  # which of the exit's goals is waited for
    exit_started_s: float | None = None
    outcome: Outcome | None = None  # how it finished


Spoken = str | None
"""The line to say next, or None when there is nothing new to say."""


def start(funnel: Funnel) -> tuple[FunnelState, Spoken]:
    return FunnelState(), funnel.levels[0].question


def answer(
    funnel: Funnel, state: FunnelState, label: str, now: float
) -> tuple[FunnelState, Spoken]:
    """Take the grade of one answer. A label outside the set counts as partial: an answer
    that could not be read gets more help, never less."""
    if state.status != "asking":
        return state, None
    if label == "unclear" and not state.repeated:
        return replace(state, repeated=True), funnel.levels[state.level].question
    state = replace(state, graded=state.graded + 1)
    if label == "correct":
        resolved = replace(state, status="resolved", outcome="correct")
        return resolved, funnel.confirmation_at(state.level)
    if state.level + 1 < len(funnel.levels):
        lower = replace(state, level=state.level + 1, repeated=False)
        return lower, funnel.levels[lower.level].question
    return replace(state, status="exit", exit_started_s=now), funnel.exit.line


def on_mat(
    funnel: Funnel, state: FunnelState, *, goal_met: bool, now: float
) -> tuple[FunnelState, Spoken]:
    """Take one look at the mat during the exit. `goal_met` says whether the goal being
    waited for (`funnel.exit.then[state.exit_goal]`) holds. Nothing is spoken here."""
    if state.status != "exit":
        return state, None
    if goal_met:
        if state.exit_goal + 1 >= len(funnel.exit.then):
            return replace(state, status="resolved", outcome="exit_done"), None
        state = replace(state, exit_goal=state.exit_goal + 1)
    started = state.exit_started_s if state.exit_started_s is not None else now
    if now - started >= funnel.exit.timeout_seconds:
        return replace(state, status="resolved", outcome="exit_timeout"), None
    return state, None
