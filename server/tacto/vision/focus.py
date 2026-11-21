"""Get the camera back in focus when it cannot read the mat.

The LogiInsight camera's autofocus can be left parked where the mat is a blur (sharpness
about 8 where a focused mat is 70 or more), and it then stays there for as long as nothing
in the picture moves. Seen after autofocus had been switched off, and after "autofocus on"
was sent before the camera was sending frames. Sending "autofocus on" while frames are
flowing makes it sweep and lock on within about two seconds. Measured on 21 Nov 2026,
docs/hardware-log.md.

So: when no corner marker has been readable for a while, kick the autofocus, and not
again until the sweep has had time to finish.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from . import exposure

# TODO(Katie): tune on the real desk. Long enough that a hand passing over the markers
# does not set off a sweep, which blurs the picture for a second or two.
KICK_AFTER_BLIND_S = 2.0
# A sweep took about two seconds; kicking during one would start it again.
KICK_EVERY_S = 5.0


class FocusKeeper:
    """Told each frame whether any corner marker was readable; kicks the autofocus when not."""

    def __init__(
        self,
        kick: Callable[[], bool] = exposure.refocus,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kick = kick
        self._clock = clock
        self._blind_since: float | None = None
        self._last_kick_s: float | None = None
        self.kicks = 0

    def saw(self, any_corner: bool) -> bool:
        """Call once a frame. True when this frame set off a focus sweep."""
        now = self._clock()
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
        self.kicks += 1
        self._kick()
        return True
