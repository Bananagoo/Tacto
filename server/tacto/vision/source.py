"""The camera as a mat source: frames in, what is on the mat and where the fingertip is out.

One thread takes the newest frame and puts it through every step:

    find the mat (tracker) -> keep the focus (focus) -> find the hand (hands)
    -> read every segment (classify) -> smooth (stable) -> pieces and fingertip

`view()` hands the lab the latest result without waiting. Nothing is read off a frame
whose mat position no corner marker backs: such a frame may be out of focus, so the pieces
hold. Recorded frames go through the same code (`frames.FramesOnAClock`).
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

import numpy as np

from ..lab import MatView
from ..mat import Mat
from ..pieces import Placed
from .classify import MatReader, PieceColours, load_colours, to_placed
from .flatten import frame_point_to_mat
from .focus import FocusKeeper
from .hands import INDEX_TIP
from .live import FrameWaiter, HandFinder
from .patches import segments
from .print_geometry import PrintGeometry
from .stable import StableReadings
from .tracker import MatTracker

# TODO(Katie): tune with a real hand on the real mat.
# A segment whose middle is this close to any point of a hand counts as covered by it.
HAND_COVERS_MM = 16.0
# A fingertip this far outside the dot grid (in grid widths) is not over the mat.
FINGER_MARGIN = 0.12
FRAME_TIMEOUT_S = 0.5
TIMING_SMOOTHING = 0.9


class CameraMatSource:
    """A `MatSource` fed by camera frames. Call `start()`, or drive it with `step()`."""

    def __init__(
        self,
        mat: Mat,
        frames: FrameWaiter,
        *,
        colours: PieceColours | None = None,
        hands: HandFinder | None = None,
        focus: FocusKeeper | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._mat = mat
        self._frames = frames
        self._geometry = PrintGeometry.for_mat(mat)
        self._tracker = MatTracker(self._geometry, clock=clock)
        self._reader = MatReader(mat, self._geometry, colours or load_colours())
        self._stable = StableReadings()
        self._hands = hands
        self._focus = focus
        self._clock = clock
        self._lock = threading.Lock()
        self._view = MatView(mat_visible=False)
        self._placed: tuple[Placed, ...] = ()
        self._timings_ms: dict[str, float] = {}
        self._frames_seen = 0
        self._seen: dict = {"corners_seen": [], "position_confirmed": False}
        self._stopping = False
        self._thread: threading.Thread | None = None

    # ---------- the lab's side ----------

    def view(self) -> MatView:
        with self._lock:
            return self._view

    def report(self) -> dict:
        """For the people running it: where each frame's time goes and what was last seen."""
        with self._lock:
            return {
                "frames": self._frames_seen,
                "mat_visible": self._view.mat_visible,
                **self._seen,
                "squares_seen": sum(self._reader.palette.seen),
                "focus_kicks": self._focus.kicks if self._focus else 0,
                "pieces": len(self._view.placed),
                "finger": self._view.finger,
                "stage_ms": {stage: round(ms, 1) for stage, ms in self._timings_ms.items()},
            }

    # ---------- the camera's side ----------

    def start(self) -> None:
        if self._thread is None:
            self._stopping = False
            self._thread = threading.Thread(target=self._run, name="mat-reader", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stopping = True
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        if self._focus is not None:
            self._focus.close()

    def _run(self) -> None:
        seq = -1
        while not self._stopping:
            got = self._frames.wait_for_frame(seq, FRAME_TIMEOUT_S)
            if got is None:
                continue
            seq, frame = got
            try:
                self.step(frame)
            except Exception as error:  # noqa: BLE001 - one bad frame must not end the reader
                print(f"vision.source: frame skipped: {error!r}")

    def step(self, frame: np.ndarray) -> None:
        """Put one frame through the whole reader."""
        timings: dict[str, float] = {}
        started = time.perf_counter()

        def lap(stage: str) -> None:
            nonlocal started
            now = time.perf_counter()
            timings[stage] = (now - started) * 1000
            started = now

        flattened = self._tracker.see(frame)
        lap("flatten")
        if self._focus is not None:
            self._focus.saw(bool(self._tracker.corners_seen))

        finger: tuple[float, float] | None = None
        if flattened is not None and self._tracker.confirmed:
            covered: set[str] = set()
            if self._hands is not None and frame.ndim == 3 and frame.shape[2] == 3:
                hands = self._hands.hands(frame, round(self._clock() * 1000))
                finger, covered = self._locate(hands, flattened.frame_to_page)
                lap("hand")
            readings = self._reader.read(flattened)
            lap("read")
            self._placed = to_placed(self._stable.update(readings, covered), self._mat)
            lap("smooth")

        with self._lock:
            self._frames_seen += 1
            self._seen = {
                "corners_seen": self._tracker.corners_seen,
                "position_confirmed": self._tracker.confirmed,
            }
            self._view = MatView(
                placed=self._placed, finger=finger, mat_visible=flattened is not None
            )
            for stage, ms in timings.items():
                old = self._timings_ms.get(stage, ms)
                self._timings_ms[stage] = TIMING_SMOOTHING * old + (1 - TIMING_SMOOTHING) * ms

    def _locate(
        self, hands: list[dict], frame_to_page: np.ndarray
    ) -> tuple[tuple[float, float] | None, set[str]]:
        """The pointing fingertip as a mat position, and the segments any hand is over."""
        points_mm: list[tuple[float, float]] = []
        tips: list[tuple[float, float]] = []
        for hand in hands:
            for number, (x_px, y_px) in enumerate(hand["points"]):
                x, y, w = frame_to_page @ np.array([x_px, y_px, 1.0])
                if abs(w) < 1e-12:
                    continue
                points_mm.append((x / w, y / w))
                if number == INDEX_TIP:
                    tips.append(
                        frame_point_to_mat(frame_to_page, self._geometry, self._mat, x_px, y_px)
                    )
        covered: set[str] = set()
        if points_mm:
            for a, b in segments(self._mat):
                (ax, ay), (bx, by) = self._geometry.dot_mm(a), self._geometry.dot_mm(b)
                middle = ((ax + bx) / 2, (ay + by) / 2)
                if any(math.dist(middle, point) <= HAND_COVERS_MM for point in points_mm):
                    covered.add(Placed("wire", a, b).id)
        over_mat = [
            tip
            for tip in tips
            if -FINGER_MARGIN <= tip[0] <= 1 + FINGER_MARGIN
            and -FINGER_MARGIN <= tip[1] <= 1 + FINGER_MARGIN
        ]
        if not over_mat:
            return None, covered
        # Two hands over the mat: the one nearer its middle is the one pointing.
        return min(over_mat, key=lambda tip: math.dist(tip, (0.5, 0.5))), covered
