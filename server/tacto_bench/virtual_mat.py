"""A mat you move with the mouse instead of your hands: the dev tools page drives it.

It is a `tacto.observation.Source`, so the real session, solver and lesson engine run on
top of it exactly as they will on top of the camera.
"""

from __future__ import annotations

import threading

from tacto.mat.models import MatLayout, SlotContent
from tacto.observation import Fingertip, Observation


class VirtualMat:
    def __init__(self, layout: MatLayout) -> None:
        self.layout = layout
        # Routes change the mat from one thread while the socket reads it from another.
        self._lock = threading.Lock()
        self._reading = layout.initial_reading()
        self._fingertip: Fingertip | None = None

    def observe(self) -> Observation:
        with self._lock:
            return Observation(reading=self._reading, fingertip=self._fingertip)

    def set_drawn(self, drawable_id: str, drawn: bool) -> None:
        if drawable_id not in {drawable.id for drawable in self.layout.drawables}:
            raise KeyError(f"this mat has no line called {drawable_id!r}")
        with self._lock:
            lines = (
                self._reading.drawn | {drawable_id}
                if drawn
                else self._reading.drawn - {drawable_id}
            )
            self._reading = self._reading.model_copy(update={"drawn": frozenset(lines)})

    def set_slot(self, slot_id: str, content: SlotContent) -> None:
        slot = next((slot for slot in self.layout.slots if slot.id == slot_id), None)
        if slot is None:
            raise KeyError(f"this mat has no slot called {slot_id!r}")
        if content != "empty" and content not in slot.accepts:
            raise ValueError(f"slot {slot_id!r} does not accept a {content}")
        with self._lock:
            slots = {**self._reading.slots, slot_id: content}
            self._reading = self._reading.model_copy(update={"slots": slots})

    def set_fingertip(self, fingertip: Fingertip | None) -> None:
        with self._lock:
            self._fingertip = fingertip

    def reset(self) -> None:
        with self._lock:
            self._reading = self.layout.initial_reading()
            self._fingertip = None
