"""The live camera and hand tracker, behind the two small interfaces `VisionSource` reads.

worker = hub.acquire(index)
source = VisionSource(layout, CameraFrames(worker), TrackedIndexFinger(HandTracker()))
source.start()
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Protocol

import numpy as np

from .hands import INDEX_TIP


class FrameWaiter(Protocol):
    """The part of `vision.camera.CameraWorker` this module uses."""

    def wait_for_frame(self, after: int, timeout: float) -> tuple[int, np.ndarray] | None: ...


class HandFinder(Protocol):
    """The part of `vision.hands.HandTracker` this module uses."""

    def hands(self, frame: np.ndarray, t_ms: int) -> list[dict]: ...


class CameraFrames:
    """A camera worker as a `FrameSource`: its newest frame, never waiting for one."""

    def __init__(self, worker: FrameWaiter) -> None:
        self._worker = worker

    def latest_frame(self) -> np.ndarray | None:
        newest = self._worker.wait_for_frame(after=-1, timeout=0)
        return None if newest is None else newest[1]


class TrackedIndexFinger:
    """A hand tracker as a `FingerFinder`. Not thread-safe, like the tracker it wraps."""

    def __init__(self, tracker: HandFinder, clock: Callable[[], float] = time.monotonic) -> None:
        self._tracker = tracker
        self._clock = clock

    def index_tip_px(self, frame: np.ndarray) -> tuple[float, float] | None:
        # The tracker converts from three colour channels and raises on anything else.
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0:
            return None
        tips = [hand["points"][INDEX_TIP] for hand in self._tracker.hands(frame, self._now_ms())]
        if not tips:
            return None
        height_px, width_px = frame.shape[:2]
        middle = (width_px / 2, height_px / 2)
        # The mat fills the frame, so the pointing hand is the one nearer its middle;
        # the other is at the edge holding the paper. Handedness labels can swap.
        x_px, y_px = min(tips, key=lambda tip: math.dist(tip, middle))
        return float(x_px), float(y_px)

    def _now_ms(self) -> int:
        return round(self._clock() * 1000)
