"""What a source reports about the desk: the mat, and where the fingertip is."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from .mat.models import MatReading


class Fingertip(BaseModel):
    """Mat position, 0..1 from the first dot column or row to the last."""

    x: float
    y: float


class Observation(BaseModel):
    reading: MatReading
    fingertip: Fingertip | None = None  # None when no hand is over the mat


class Source(Protocol):
    """Anything that can look at the desk: the camera, recorded frames, or a test."""

    def observe(self) -> Observation: ...
