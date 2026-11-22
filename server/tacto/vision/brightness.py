"""Automatic brightness, metered on the paper of the mat.

The camera's own auto-exposure meters the whole picture, so a dark desk or floor makes it
burn the white mat out. Exposure is therefore manual (`exposure.py`), and this steers the
camera's gain so that the paper, measured on the flattened mat every frame, sits near
TARGET_PAPER of 255 whatever the room's light. It never lets the paper clip to pure white,
which would wash out the colour squares and the markers.

It calibrates, then holds still. Every change of gain shifts every colour the reader sees,
and a hand or a shadow on the mat changes the paper's level, so once it has found a setting
it is `locked` and leaves the camera alone until `recalibrate()` is called (the setup check
does, and so does a start). Live on 22 Nov 2026 it never stopped: a shiny spot clipped (so
down) while the paper read dim (so up), every 0.4 s.

It is a small state machine:

    waiting      no paper measured yet (the mat is not found)
    adjusting    calibrating: the paper is off target; the gain is being stepped towards it
    settled      locked: the paper is within DEADBAND of the target
    glare        locked: the paper is dim, but one step brighter clips a shiny spot, so it
                 holds the brightest setting that does not
    too dark     locked: at MAX_GAIN and still dim: more light is needed in the room
    too bright   locked: at gain 0 and still too bright: less light, or move out of the glare
    unavailable  the camera's gain cannot be set (uvc-util missing, or no camera)

Calibrating stops after CALIBRATE_LIMIT_S whatever the readings, so it always ends held.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Literal

import cv2
import numpy as np

# TODO(Katie): tune at the venue. On the demo desk, gain 0 put the paper at 181 and gain 30 at
# 245 (docs/hardware-log.md), about 2 per step; gain 40 already clipped most of the page.
TARGET_PAPER = 200.0
DEADBAND = 12.0
MAX_GAIN = 40
# Paper this bright counts as clipped, and more than this share of clipped page backs off.
CLIP_LEVEL = 250
MAX_CLIPPED = 0.01
# One change at most this often: the camera takes a few frames to show a new gain.
PERIOD_S = 0.4
LARGEST_STEP = 6
# Calibration ends here at the latest, and the setting it reached is held.
CALIBRATE_LIMIT_S = 10.0

State = Literal["waiting", "adjusting", "settled", "glare", "too dark", "too bright", "unavailable"]


def paper_level(page: np.ndarray) -> tuple[float, float]:
    """How bright the paper is (0..255, the median of the brightest channel, which is the
    paper because most of the page is paper) and what share of the page is clipped white."""
    small = cv2.resize(page, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    brightest = small.max(axis=2)
    return float(np.median(brightest)), float((brightest >= CLIP_LEVEL).mean())


class AutoGain:
    """Told the paper's level every frame; steps the camera's gain towards the target."""

    def __init__(
        self,
        apply_gain: Callable[[int], bool],
        *,
        start_gain: int = 0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._apply = apply_gain
        self._clock = clock
        self.gain = start_gain
        self.state: State = "waiting"
        self.paper: float | None = None
        self.clipped: float | None = None
        self._last_change_s: float | None = None
        self._failures = 0
        self.locked = False
        self._began_s: float | None = None
        # The lowest gain seen to clip, and the highest seen not to: the search runs between.
        self._ceiling = MAX_GAIN + 1
        self._last_good: int | None = None

    def recalibrate(self) -> None:
        """Find the setting again, for the room's light now (the setup check calls this)."""
        self.locked = False
        self._began_s = None
        self._last_change_s = None
        self._ceiling = MAX_GAIN + 1
        self._last_good = None
        if self.state != "unavailable":
            self.state = "adjusting" if self.paper is not None else "waiting"

    def _hold(self, state: State) -> None:
        self.state = state
        self.locked = True

    def saw(self, paper: float | None, clipped: float | None) -> None:
        """Call once a frame with `paper_level`'s two numbers, or None when no mat is seen."""
        if paper is None or clipped is None:
            return
        self.paper, self.clipped = paper, clipped
        if self.state == "unavailable" or self.locked:
            return
        now = self._clock()
        if self._began_s is None:
            self._began_s = now
        if now - self._began_s >= CALIBRATE_LIMIT_S:
            self._hold("settled" if abs(TARGET_PAPER - paper) <= DEADBAND else self.state)
            return
        if self._last_change_s is not None and now - self._last_change_s < PERIOD_S:
            return
        error = TARGET_PAPER - paper
        if clipped > MAX_CLIPPED:
            # Clipped paper has lost its colour: come down, whatever the median says. Halfway
            # back to the last setting that did not clip, so a glare spot is closed in on, not
            # swung across.
            self._ceiling = min(self._ceiling, self.gain)
            if self._last_good is not None and self._last_good < self.gain:
                wanted = (self._last_good + self.gain) // 2
            else:
                wanted = self.gain - LARGEST_STEP
        else:
            self._last_good = self.gain
            if abs(error) <= DEADBAND:
                self._hold("settled")
                return
            # About 2 levels of paper per step of gain; go two-thirds of the way each time,
            # so it closes in without overshooting. Never up into a gain seen to clip.
            step = int(np.clip(round(abs(error) / 3), 1, LARGEST_STEP))
            wanted = self.gain + (step if error > 0 else -step)
            if error > 0 and self._ceiling <= MAX_GAIN and wanted >= self._ceiling:
                wanted = self._ceiling - 1
                if wanted <= self.gain:
                    self._hold("glare")
                    return
        wanted = int(np.clip(wanted, 0, MAX_GAIN))
        if wanted == self.gain:
            self._hold("too dark" if error > 0 else "too bright")
            return
        self._last_change_s = now
        if not self._apply(wanted):
            self._failures += 1
            if self._failures >= 2:
                self.state = "unavailable"
            return
        self._failures = 0
        self.gain = wanted
        self.state = "adjusting"
