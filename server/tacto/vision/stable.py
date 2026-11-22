"""Readings that do not flicker: a segment changes only after several frames agree.

One frame can be wrong: a hand's shadow, a piece half laid down, a blurred frame. So a
segment keeps its answer until the same new answer has been read a few frames running.
A segment the reader is unsure of, or that a hand is over, keeps its answer for as long
as that lasts: a piece does not vanish because someone reached across it.
"""

from __future__ import annotations

from collections.abc import Collection

from .classify import Reading

# TODO(Katie): tune on the real mat. At about 17 frames a second, 3 frames is 0.2 s.
FRAMES_TO_CHANGE = 3

_EMPTY = Reading("empty", 0.0)


class StableReadings:
    """Feed it every frame's readings; `current` is what the mat is taken to hold."""

    def __init__(self, frames_to_change: int = FRAMES_TO_CHANGE) -> None:
        self._needed = frames_to_change
        self.current: dict[str, Reading] = {}
        self._candidate: dict[str, tuple[tuple, int]] = {}

    def update(
        self,
        readings: dict[str, Reading],
        covered: Collection[str] = (),
        *,
        frames_to_change: int | None = None,
    ) -> dict[str, Reading]:
        """Take one frame's readings. `covered` are segments a hand is over.
        `frames_to_change` asks for more agreeing frames than usual for this frame's
        changes, for when a hand is about. Returns `current`."""
        needed = frames_to_change or self._needed
        for segment, reading in readings.items():
            if reading.piece == "unsure" or segment in covered:
                # Not evidence for anything, and not evidence against a change under way.
                continue
            seen = (reading.piece, reading.positive)
            held = self.current.get(segment, _EMPTY)
            if seen == (held.piece, held.positive):
                self._candidate.pop(segment, None)
                self.current[segment] = reading  # same answer, fresher cover
                continue
            candidate, count = self._candidate.get(segment, (None, 0))
            count = count + 1 if candidate == seen else 1
            if count >= needed:
                self._candidate.pop(segment, None)
                self.current[segment] = reading
            else:
                self._candidate[segment] = (seen, count)
        return self.current
