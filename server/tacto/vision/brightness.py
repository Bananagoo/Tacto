"""Automatic brightness, metered on the paper of the mat.

The camera's own auto-exposure meters the whole picture, so a dark desk or floor makes it
burn the white mat out. Exposure is therefore manual (`exposure.py`), and this steers the
camera's gain so that the paper, measured on the flattened mat every frame, sits near
TARGET_PAPER of 255 whatever the room's light. It never lets the paper clip to pure white,
which would wash out the colour squares and the markers.

It is a small state machine:

    waiting      no paper measured yet (the mat is not found)
    adjusting    the paper is off target; the gain is being stepped towards it
    settled      the paper is within DEADBAND of the target
    too dark     at MAX_GAIN and still dim: more light is needed in the room
    too bright   at gain 0 and still too bright: less light, or move out of the glare
    unavailable  the camera's gain cannot be set (uvc-util missing, or no camera)
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

State = Literal["waiting", "adjusting", "settled", "too dark", "too bright", "unavailable"]


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

    def saw(self, paper: float | None, clipped: float | None) -> None:
        """Call once a frame with `paper_level`'s two numbers, or None when no mat is seen."""
        if paper is None or clipped is None:
            return
        self.paper, self.clipped = paper, clipped
        if self.state == "unavailable":
            return
        now = self._clock()
        if self._last_change_s is not None and now - self._last_change_s < PERIOD_S:
            return
        error = TARGET_PAPER - paper
        if clipped > MAX_CLIPPED:
            # Clipped paper has lost its colour: come down fast, whatever the median says.
            wanted = self.gain - LARGEST_STEP
        elif abs(error) <= DEADBAND:
            self.state = "settled"
            return
        else:
            # About 2 levels of paper per step of gain; go two-thirds of the way each time,
            # so it closes in without overshooting.
            step = int(np.clip(round(abs(error) / 3), 1, LARGEST_STEP))
            wanted = self.gain + (step if error > 0 else -step)
        wanted = int(np.clip(wanted, 0, MAX_GAIN))
        if wanted == self.gain:
            self.state = "too dark" if error > 0 else "too bright"
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
