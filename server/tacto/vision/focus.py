"""Get the camera back in focus when it cannot read the mat.

The LogiInsight camera's autofocus can be left parked where the mat is a blur (sharpness
about 8 where a focused mat is 70 or more), and it then stays there for as long as nothing
in the picture moves, with autofocus reporting on. What starts a sweep is switching
autofocus off and, a moment later, on again while frames are flowing: the mat is sharp
about two seconds after. Sending "on" when it is already on does nothing, and off and on
in the same breath does nothing. Measured on 21 and 22 Nov 2026, docs/hardware-log.md.

So: when no corner marker has been readable for a while, switch autofocus off, switch it
back on shortly after, and do not try again until the sweep has had time to finish.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from . import exposure

# TODO(Katie): tune on the real desk. Long enough that a hand passing over the markers
# does not set off a sweep, which blurs the picture for a second or two.
KICK_AFTER_BLIND_S = 2.0
# One second apart worked every time; in the same command never did.
OFF_FOR_S = 1.0
# A sweep took about two seconds after the switch back on.
KICK_EVERY_S = 6.0


class FocusKeeper:
    """Told each frame whether any corner marker was readable; kicks the autofocus when not."""

    def __init__(
        self,
        set_autofocus: Callable[[bool], bool] = exposure.set_autofocus,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._set_autofocus = set_autofocus
        self._clock = clock
        self._blind_since: float | None = None
        self._last_kick_s: float | None = None
        self._back_on_at: float | None = None
        self.kicks = 0

    def saw(self, any_corner: bool) -> bool:
        """Call once a frame. True when this frame began a kick."""
        now = self._clock()
        if self._back_on_at is not None:
            # Half-way through a kick: finish it whatever the picture shows, so autofocus
            # is never left off.
            if now >= self._back_on_at:
                self._back_on_at = None
                self._set_autofocus(True)
            return False
        if any_corner:
            self._blind_since = None
            return False
        if self._blind_since is None:
            self._blind_since = now
        if now - self._blind_since < KICK_AFTER_BLIND_S:
            return False
        if self._last_kick_s is not None and now - self._last_kick_s < KICK_EVERY_S:
            return False
        self._last_kick_s = now
        self._back_on_at = now + OFF_FOR_S
        self.kicks += 1
        self._set_autofocus(False)
        return True

    def close(self) -> None:
        """Call when the camera is given up. Finishes a kick caught half-way."""
        if self._back_on_at is not None:
            self._back_on_at = None
            self._set_autofocus(True)
