"""Where frames come from, and where a fingertip is in one: the camera's seams.

The mat reader is written against these, so it runs the same from the live camera,
from a folder of recorded frames, and in tests.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


class FrameSource(Protocol):
    """A camera worker, a folder of recordings, or a test."""

    def latest_frame(self) -> np.ndarray | None:
        """The newest frame, or None when there is none yet. Must not block."""
        ...


class FingerFinder(Protocol):
    def index_tip_px(self, frame: np.ndarray) -> tuple[float, float] | None:
        """The index fingertip in frame pixels, or None when no hand is found."""
        ...


class FramesOnAClock:
    """A `FrameSource` handed out at a steady rate, as a camera worker hands out frames.

    This is what lets recorded frames drive the same reader loop as the live camera.
    """

    def __init__(self, source: FrameSource, *, fps: float = 10.0) -> None:
        self._source = source
        self._period_s = 1.0 / fps
        self._seq = -1

    def wait_for_frame(self, after: int, timeout: float) -> tuple[int, np.ndarray] | None:
        time.sleep(min(self._period_s, max(timeout, 0.0)))
        frame = self._source.latest_frame()
        if frame is None:
            return None
        self._seq = max(self._seq, after) + 1
        return self._seq, frame


class FolderFrames:
    """Recorded frames from a folder, one per call in name order, round and round.

    This is replay mode: the lab runs from `server/fixtures/` with no camera.
    """

    def __init__(self, directory: Path) -> None:
        self._paths = (
            sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
            if directory.is_dir()
            else []
        )
        self._next = 0

    def latest_frame(self) -> np.ndarray | None:
        # A file that is not a picture after all is passed over; one full round of
        # those means there is nothing to show.
        for _ in range(len(self._paths)):
            path = self._paths[self._next]
            self._next = (self._next + 1) % len(self._paths)
            frame = cv2.imread(str(path))
            if frame is not None:
                return frame
        return None
