"""The adapters that put the real camera worker and hand tracker behind the source."""

import time

import numpy as np

from tacto.vision.camera import CameraWorker
from tacto.vision.hands import INDEX_TIP
from tacto.vision.live import CameraFrames, TrackedIndexFinger


class CountingCapture:
    """Stands in for a cv2.VideoCapture: each read is a new frame filled with its number."""

    def __init__(self) -> None:
        self.reads = 0
        self.released = False

    def read(self) -> tuple[bool, np.ndarray]:
        time.sleep(0.002)
        self.reads += 1
        return True, np.full((4, 4, 3), self.reads % 256, np.uint8)

    def release(self) -> None:
        self.released = True


class StalledCapture(CountingCapture):
    def read(self) -> tuple[bool, None]:
        time.sleep(0.002)
        return False, None


def hand(index_tip: tuple[int, int]) -> dict:
    points = [[0, 0]] * 21
    points[INDEX_TIP] = list(index_tip)
    return {"handedness": "Right", "points": points}


class ScriptedTracker:
    def __init__(self, hands: list[dict]) -> None:
        self._hands = hands
        self.times_ms: list[int] = []

    def hands(self, frame: np.ndarray, t_ms: int) -> list[dict]:
        self.times_ms.append(t_ms)
        return self._hands


def test_camera_frames_hands_over_the_workers_newest_frame_without_waiting():
    worker = CameraWorker(0, CountingCapture())
    try:
        frames = CameraFrames(worker)
        deadline = time.monotonic() + 5
        while frames.latest_frame() is None and time.monotonic() < deadline:
            time.sleep(0.005)
        first = frames.latest_frame()
        assert first is not None
        time.sleep(0.05)
        later = frames.latest_frame()
        assert later is not first, "a new frame is a new array, which is how the source knows"
    finally:
        worker.stop()


def test_camera_frames_has_nothing_while_the_camera_sends_nothing():
    worker = CameraWorker(0, StalledCapture())
    try:
        started = time.perf_counter()
        assert CameraFrames(worker).latest_frame() is None
        assert time.perf_counter() - started < 0.05
    finally:
        worker.stop()


def test_the_index_tip_of_the_only_hand_is_reported_in_pixels():
    finger = TrackedIndexFinger(ScriptedTracker([hand((300, 200))]))
    assert finger.index_tip_px(np.zeros((480, 640, 3), np.uint8)) == (300.0, 200.0)


def test_with_two_hands_the_one_pointing_nearer_the_middle_of_the_frame_wins():
    # The other hand is usually at the edge, holding the paper still. Handedness labels
    # can swap between frames, so they are not used.
    tracker = ScriptedTracker([hand((20, 460)), hand((330, 250))])
    assert TrackedIndexFinger(tracker).index_tip_px(np.zeros((480, 640, 3), np.uint8)) == (330, 250)


def test_no_hand_means_no_fingertip():
    finger = TrackedIndexFinger(ScriptedTracker([]))
    assert finger.index_tip_px(np.zeros((480, 640, 3), np.uint8)) is None


def test_the_tracker_is_given_the_time_in_milliseconds():
    tracker = ScriptedTracker([])
    finger = TrackedIndexFinger(tracker, clock=lambda: 12.3456)
    finger.index_tip_px(np.zeros((480, 640, 3), np.uint8))
    assert tracker.times_ms == [12346]


def test_a_frame_the_tracker_cannot_take_is_not_passed_to_it():
    # MediaPipe wants three colour channels and would raise on anything else.
    tracker = ScriptedTracker([hand((1, 1))])
    finger = TrackedIndexFinger(tracker)
    for frame in (
        np.zeros((480, 640), np.uint8),
        np.zeros((480, 640, 4), np.uint8),
        np.zeros((0, 0, 3), np.uint8),
    ):
        assert finger.index_tip_px(frame) is None
    assert tracker.times_ms == []
