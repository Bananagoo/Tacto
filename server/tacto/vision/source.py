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

import cv2
import numpy as np

from ..lab import MatView
from ..mat import Mat
from ..pieces import Placed
from .brightness import AutoGain, paper_level
from .classify import MatReader, PieceColours, closest_colours, load_colours, to_placed
from .flatten import frame_point_to_mat
from .focus import FocusKeeper
from .hands import INDEX_TIP
from .live import FrameWaiter, HandFinder
from .patches import segments
from .print_geometry import REFERENCE_SQUARES, PrintGeometry
from .stable import StableReadings
from .tracker import MatTracker

# TODO(Katie): tune with a real hand on the real mat.
# The tracker gives 21 joints, not the hand's outline. The hand is taken to be the shape
# stretched round them, this much wider all round: fingers are thick and joints jitter.
HAND_MARGIN_MM = 14.0
# The arm is not tracked at all. It is taken to run on from the wrist, away from the
# fingers, as wide as the knuckles, off the edge of the page.
FOREARM_MM = 400.0
WRIST, INDEX_KNUCKLE, MIDDLE_KNUCKLE, LITTLE_KNUCKLE = 0, 5, 9, 17
# A fast hand is lost for a few frames at a time. What it covered stays covered this long
# after it was last seen there, so those frames cannot change anything under it.
HAND_LINGER_S = 0.5
# While a hand is about, a change anywhere needs this many agreeing frames, not three:
# shadows and the edges of a moving hand reach further than its outline.
FRAMES_TO_CHANGE_NEAR_HAND = 8
# A fingertip this far outside the dot grid (in grid widths) is not over the mat.
FINGER_MARGIN = 0.12
FRAME_TIMEOUT_S = 0.5
TIMING_SMOOTHING = 0.9


def _hand_and_arm(joints: dict[int, tuple[float, float]]) -> np.ndarray:
    """The page area a hand and its arm lie over, from the hand's joints in page
    millimetres: the points of a shape to stretch a hull round."""
    points = list(joints.values())
    needed = (WRIST, INDEX_KNUCKLE, MIDDLE_KNUCKLE, LITTLE_KNUCKLE)
    if all(joint in joints for joint in needed):
        wrist = np.array(joints[WRIST])
        up_the_arm = wrist - np.array(joints[MIDDLE_KNUCKLE])
        length = float(np.linalg.norm(up_the_arm))
        half_width = math.dist(joints[INDEX_KNUCKLE], joints[LITTLE_KNUCKLE]) / 2
        if length > 1e-6 and half_width > 1e-6:
            up_the_arm /= length
            across = np.array([-up_the_arm[1], up_the_arm[0]]) * half_width
            elbow = wrist + up_the_arm * FOREARM_MM
            points += [tuple(wrist + across), tuple(wrist - across)]
            points += [tuple(elbow + across), tuple(elbow - across)]
    return np.float32(points)


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
        brightness: AutoGain | None = None,
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
        # Steers the camera's gain to keep the paper near a set brightness (brightness.py).
        self._brightness = brightness
        self._clock = clock
        self._unsure = 0
        # The last confirmed look at the mat, for the setup check's live view.
        self._last_look: tuple[np.ndarray, dict] | None = None
        self._last_frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._view = MatView(mat_visible=False)
        self._placed: tuple[Placed, ...] = ()
        self._covered_until: dict[str, float] = {}
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
                # What each colour square reads as now (CIELAB, paper = 100, 0, 0). If two
                # of these come close together, the reader will confuse those two pieces.
                "squares": {
                    name: [round(float(value), 1) for value in row]
                    for name, row in zip(REFERENCE_SQUARES, self._reader.palette.lab, strict=True)
                },
                "focus_kicks": self._focus.kicks if self._focus else 0,
                "brightness": self._brightness_report(),
                "closest_colours": self._closest_colours(),
                "unsure_segments": self._unsure,
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
            now = self._clock()
            if self._hands is not None and frame.ndim == 3 and frame.shape[2] == 3:
                hands = self._hands.hands(frame, round(now * 1000))
                finger, under_hand = self._locate(hands, flattened.frame_to_page)
                for segment in under_hand:
                    self._covered_until[segment] = now + HAND_LINGER_S
                lap("hand")
            self._covered_until = {s: t for s, t in self._covered_until.items() if t >= now}
            if self._brightness is not None:
                self._brightness.saw(*paper_level(flattened.image))
            readings = self._reader.read(flattened)
            self._unsure = sum(reading.piece == "unsure" for reading in readings.values())
            look = (flattened.image, readings)
            lap("read")
            stable = self._stable.update(
                readings,
                self._covered_until,
                frames_to_change=FRAMES_TO_CHANGE_NEAR_HAND if self._covered_until else None,
            )
            self._placed = to_placed(stable, self._mat)
            lap("smooth")

        with self._lock:
            self._last_frame = frame
            if flattened is not None and self._tracker.confirmed:
                self._last_look = look
            elif flattened is None:
                self._last_look = None
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

    def last_look(self) -> tuple[np.ndarray, dict] | None:
        """The last flattened mat the reader read, and what it read on it; None while the
        mat is not found. The picture is not copied: draw on a copy."""
        with self._lock:
            return self._last_look

    def last_frame(self) -> np.ndarray | None:
        """The last camera frame as it came in, for the setup check's live view. Not copied."""
        with self._lock:
            return self._last_frame

    def _brightness_report(self) -> dict:
        auto = self._brightness
        if auto is None:
            return {"state": "off"}
        return {
            "state": auto.state,
            "gain": auto.gain,
            "paper": None if auto.paper is None else round(auto.paper, 1),
            "clipped": None if auto.clipped is None else round(auto.clipped, 3),
        }

    def _closest_colours(self) -> dict:
        first, second, degrees = closest_colours(self._reader.palette)
        return {"pair": [first, second], "degrees": round(degrees, 1)}

    def _locate(
        self, hands: list[dict], frame_to_page: np.ndarray
    ) -> tuple[tuple[float, float] | None, set[str]]:
        """The pointing fingertip as a mat position, and the segments any hand is over."""
        outlines: list[np.ndarray] = []
        tips: list[tuple[float, float]] = []
        for hand in hands:
            joints: dict[int, tuple[float, float]] = {}
            for number, (x_px, y_px) in enumerate(hand["points"]):
                x, y, w = frame_to_page @ np.array([x_px, y_px, 1.0])
                if abs(w) < 1e-12:
                    continue
                joints[number] = (float(x / w), float(y / w))
                if number == INDEX_TIP:
                    tips.append(
                        frame_point_to_mat(frame_to_page, self._geometry, self._mat, x_px, y_px)
                    )
            if joints:
                outlines.append(_hand_and_arm(joints))
        covered = self._under(outlines)
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

    def _under(self, outlines: list[np.ndarray]) -> set[str]:
        """The segments any of the hands and arms lie over."""
        covered: set[str] = set()
        hulls = [cv2.convexHull(outline) for outline in outlines]
        for a, b in segments(self._mat):
            (ax, ay), (bx, by) = self._geometry.dot_mm(a), self._geometry.dot_mm(b)
            # The stretch of the segment its patch is cut from: the middle and both ends.
            along = [(ax + (bx - ax) * t, ay + (by - ay) * t) for t in (0.2, 0.5, 0.8)]
            for hull, outline in zip(hulls, outlines, strict=True):
                if len(hull) >= 3:
                    near = any(
                        cv2.pointPolygonTest(hull, point, True) >= -HAND_MARGIN_MM
                        for point in along
                    )
                else:  # a hand seen as one point or a line: no shape to stretch
                    near = any(
                        math.dist(point, tuple(joint)) <= HAND_MARGIN_MM
                        for point in along
                        for joint in outline
                    )
                if near:
                    covered.add(Placed("wire", a, b).id)
                    break
        return covered
