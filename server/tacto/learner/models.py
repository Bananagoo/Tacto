"""What we remember about a learner. Answers and mastery only: nothing from the camera or mic."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..contract import Mastery


class ConceptProgress(BaseModel):
    mastery: Mastery = "unseen"
    correct: int = 0  # predictions about this concept that were right
    wrong: int = 0


class Progress(BaseModel):
    """One learner's standing across every lesson they have touched."""

    concepts: dict[str, ConceptProgress] = {}  # concept id -> progress
    completed_steps: dict[str, list[str]] = {}  # lesson id -> step ids, in the order finished


class Attempt(BaseModel):
    """One prediction."""

    lesson_id: str
    step_id: str
    choice: str
    correct: bool
    at: datetime
