"""The camera as a `tacto.observation.Source`: frames in, a steady Observation out.

Hands are over the mat all the time, hiding corners, tiles and lines for a moment.
So the source never trusts one frame: it keeps what it last knew whenever the mat
cannot be seen, and lets a change through only once it has held for a few frames.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Generic, Protocol, TypeVar

import cv2
import numpy as np

from ..mat.models import MatLayout, MatReading
from ..observation import Fingertip, Observation
from .flatten import flatten, frame_point_to_mat
from .print_geometry import PrintGeometry
from .reader import read_mat

# A changed line or slot is believed after this many frames in a row agree on it.
# TODO(vision owner): at 30 frames a second this is a tenth of a second, which also
# means a hand resting on a tile empties its slot that fast. Raise it if tiles flicker
# on the real desk; every extra frame adds 33 ms before a real change shows.
STABLE_FRAMES = 3
# A fingertip this far outside the dot grid, in dot spacings, is no longer on the mat.
FINGER_MARGIN_DOTS = 0.5
# How long the background thread sleeps when the camera has nothing new.
IDLE_POLL_S = 0.005

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}

T = TypeVar("T")


class FrameSource(Protocol):
    """Where frames come from: a camera worker, a folder of recordings, or a test."""

    def latest_frame(self) -> np.ndarray | None:
        """The newest frame without waiting for one, or None if there is none yet.

        Every new frame must be a new array: the source tells frames apart by identity.
        """
        ...


class FingerFinder(Protocol):
    def index_tip_px(self, frame: np.ndarray) -> tuple[float, float] | None:
        """The index fingertip in frame pixels, or None when no hand is in the frame."""
        ...


class _Steady(Generic[T]):
    """One value that changes only after a new value has been offered several times running."""

    def __init__(self, value: T) -> None:
        self.value = value
        self._candidate = value
        self._times_seen = 0

    def offer(self, value: T) -> None:
        if value == self.value:
            self._times_seen = 0
            return
        if value != self._candidate:
            self._candidate, self._times_seen = value, 0
        self._times_seen += 1
        if self._times_seen >= STABLE_FRAMES:
            self.value, self._times_seen = value, 0


class VisionSource:
    """Reads the mat and the fingertip from frames. Satisfies `tacto.observation.Source`.

    By default each new frame is processed inside `observe()`, which suits replay and
    tests. With a live camera call `start()`: frames are then processed on a thread of
    their own and `observe()` only hands back the latest result, so the server's event
    loop never waits on OpenCV or the hand tracker.
    """

    def __init__(
        self, layout: MatLayout, frames: FrameSource, fingers: FingerFinder | None = None
    ) -> None:
        self._layout = layout
        self._geometry = PrintGeometry.for_layout(layout)
        self._frames = frames
        self._fingers = fingers
        initial = layout.initial_reading()
        # Each line and each slot settles on its own, so a hand fidgeting over one
        # tile does not hold back a line drawn somewhere else.
        self._drawn = {drawable.id: _Steady(False) for drawable in layout.drawables}
        self._slots = {slot.id: _Steady(initial.slots[slot.id]) for slot in layout.slots}
        self._frame_to_page: np.ndarray | None = None
        self._last_frame: np.ndarray | None = None
        self._observation = Observation(reading=initial)
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

    def observe(self) -> Observation:
        if self._thread is None:
            self._process_new_frame()
        return self._observation

    def start(self) -> None:
        """Process frames on a background thread from now on."""
        if self._thread is not None:
            return
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run, name="vision-source", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stopping.set()
        self._thread.join(timeout=3)
        self._thread = None

    def _run(self) -> None:
        while not self._stopping.is_set():
            if not self._process_new_frame():
                self._stopping.wait(IDLE_POLL_S)

    def _process_new_frame(self) -> bool:
        """Look at the latest frame if it has not been looked at yet. True if it was new."""
        frame = self._frames.latest_frame()
        if frame is None or frame is self._last_frame:
            return False
        self._last_frame = frame
        flattened = flatten(frame, self._geometry)
        # With a corner hidden the mat cannot be read; what was last seen still stands,
        # and the last mapping still places the fingertip.
        if flattened is not None:
            self._frame_to_page = flattened.frame_to_page
            self._take_in(read_mat(flattened, self._layout, self._geometry))
        self._observation = Observation(reading=self._reading(), fingertip=self._fingertip(frame))
        return True

    def _take_in(self, seen: MatReading) -> None:
        for drawable_id, steady in self._drawn.items():
            steady.offer(drawable_id in seen.drawn)
        for slot_id, steady in self._slots.items():
            steady.offer(seen.slots.get(slot_id, "empty"))

    def _reading(self) -> MatReading:
        return MatReading(
            drawn=frozenset(drawable_id for drawable_id, s in self._drawn.items() if s.value),
            slots={slot_id: steady.value for slot_id, steady in self._slots.items()},
        )

    def _fingertip(self, frame: np.ndarray) -> Fingertip | None:
        if self._fingers is None or self._frame_to_page is None:
            return None
        tip_px = self._fingers.index_tip_px(frame)
        if tip_px is None:
            return None
        x, y = frame_point_to_mat(self._frame_to_page, self._geometry, self._layout, *tip_px)
        margin_x = FINGER_MARGIN_DOTS / (self._layout.cols - 1)
        margin_y = FINGER_MARGIN_DOTS / (self._layout.rows - 1)
        if not (-margin_x <= x <= 1 + margin_x and -margin_y <= y <= 1 + margin_y):
            return None
        return Fingertip(x=x, y=y)


class FolderFrames:
    """Recorded frames from a folder, one per call in name order, round and round.

    This is replay mode: the product runs from `server/fixtures/` with no camera.
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
