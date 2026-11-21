"""A tap on the paper switch: a fingertip that rests on it for about half a second.

The camera sees where a fingertip is, not whether it presses. So a tap is a dwell,
and the finger must leave the switch before it can tap again; otherwise a finger
left resting on the switch would flick it open and closed for ever.
"""

from __future__ import annotations

# TODO(vision owner): tune with a real hand; long enough that a hand passing over
# the switch does not toggle it, short enough to feel like a tap.
DWELL_SECONDS = 0.5


class SwitchTaps:
    """Feed it the switch under the fingertip on every look at the mat."""

    def __init__(self) -> None:
        self._on: str | None = None
        self._since = 0.0
        self._fired = False

    def update(self, switch_id: str | None, now: float) -> str | None:
        """The id of the switch tapped just now, else None.

        `switch_id` is the switch under the fingertip, or None when the fingertip is
        on anything else or there is no hand.
        """
        if switch_id != self._on:
            self._on, self._since, self._fired = switch_id, now, False
            return None
        if switch_id is not None and not self._fired and now - self._since >= DWELL_SECONDS:
            self._fired = True
            return switch_id
        return None
