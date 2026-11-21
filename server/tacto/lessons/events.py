"""What the lesson engine reports. The engine never saves anything: whoever runs it
drains these events and decides what to store."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PredictionMade(BaseModel):
    """The learner committed to one of a step's choices."""

    step_id: str
    choice: str
    correct: bool
    at: datetime


class StepCompleted(BaseModel):
    """The learner heard a step's explanation and moved on."""

    step_id: str
    teaches: list[str]  # concept ids
    correct: bool | None  # the step's prediction result; None when it asked for none
    at: datetime


class LessonCompleted(BaseModel):
    """The last step of the lesson was completed."""

    lesson_id: str
    at: datetime


LessonEvent = PredictionMade | StepCompleted | LessonCompleted
