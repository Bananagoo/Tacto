"""The interface between the app and whatever produces the world it shows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .contract import ClientMessage, State


class World(Protocol):
    """One learner's view of the bench. The app polls `state` and forwards messages."""

    def state(self) -> State: ...

    def handle(self, message: ClientMessage) -> None: ...


WorldFactory = Callable[[], World]
"""Called once per WebSocket connection."""
