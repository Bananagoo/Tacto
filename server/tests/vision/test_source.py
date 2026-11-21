"""The vision source: frames in, a steady Observation out."""

import time

import cv2
import numpy as np
import pytest
from vision_scenes import STRAIGHT, UPSIDE_DOWN, Scene, View, frame_position

from tacto.mat.models import MatReading
from tacto.observation import Observation
from tacto.vision.source import STABLE_FRAMES, FolderFrames, VisionSource


class ShownFrames:
    """A camera the test holds pictures up to."""

    def __init__(self) -> None:
        self._frame: np.ndarray | None = None

    def show(self, frame: np.ndarray) -> None:
        self._frame = frame.copy()  # a camera delivers every frame as a new array

    def latest_frame(self) -> np.ndarray | None:
        return self._frame


class PointingFinger:
    """A hand tracker that reports wherever the test says the fingertip is."""

    def __init__(self, tip_px: tuple[float, float] | None = None) -> None:
        self.tip_px = tip_px
        self.frames_seen = 0

    def index_tip_px(self, frame: np.ndarray) -> tuple[float, float] | None:
        self.frames_seen += 1
        return self.tip_px


class Desk:
    """A source with its fake camera and fake hand tracker."""

    def __init__(self, layout) -> None:
        self.frames = ShownFrames()
        self.finger = PointingFinger()
        self.source = VisionSource(layout, self.frames, self.finger)

    def show(self, frame: np.ndarray, times: int = 1) -> Observation:
        for _ in range(times):
            self.frames.show(frame)
            observation = self.source.observe()
        return observation


@pytest.fixture(scope="module")
def shipped(layout) -> np.ndarray:
    return Scene(layout).place_starting_tiles().photograph()


@pytest.fixture(scope="module")
def gap_drawn(layout) -> np.ndarray:
    return Scene(layout).place_starting_tiles().draw_line("gap").photograph()


@pytest.fixture(scope="module")
def tile_covered(layout) -> np.ndarray:
    return Scene(layout).place_starting_tiles().cover_slot("tile").photograph()


@pytest.fixture(scope="module")
def corner_covered(layout) -> np.ndarray:
    return Scene(layout).place_starting_tiles().draw_line("gap").cover_corner(2).photograph()


@pytest.fixture
def desk(layout) -> Desk:
    return Desk(layout)


def test_before_any_frame_the_mat_is_as_the_kit_ships(desk, layout):
    assert desk.source.observe() == Observation(reading=layout.initial_reading(), fingertip=None)


def test_a_change_appears_only_after_three_consecutive_frames(desk, layout, shipped, gap_drawn):
    assert STABLE_FRAMES == 3
    assert desk.show(shipped, times=5).reading == layout.initial_reading()
    assert desk.show(gap_drawn).reading.drawn == frozenset()
    assert desk.show(gap_drawn).reading.drawn == frozenset()
    assert desk.show(gap_drawn).reading.drawn == {"gap"}
    assert desk.show(gap_drawn, times=5).reading.drawn == {"gap"}


def test_a_single_odd_frame_is_ignored(desk, shipped, gap_drawn):
    desk.show(shipped, times=3)
    desk.show(gap_drawn)
    desk.show(shipped)  # the count starts again
    assert desk.show(gap_drawn, times=2).reading.drawn == frozenset()
    assert desk.show(gap_drawn).reading.drawn == {"gap"}


def test_a_tile_taken_off_is_only_empty_once_the_bare_slot_has_been_seen_three_times(desk, layout):
    wire, bare = Scene(layout).place_tile("tile", "wire"), Scene(layout)
    desk.show(wire.photograph(), times=3)
    assert desk.show(bare.photograph(), times=2).reading.slots["tile"] == "wire"
    assert desk.show(bare.photograph()).reading.slots["tile"] == "empty"


def test_a_hand_passing_over_a_tile_does_not_empty_its_slot(desk, shipped, tile_covered):
    desk.show(shipped, times=3)
    for _ in range(4):  # a hand flickering in and out of the way
        assert desk.show(tile_covered, times=STABLE_FRAMES - 1).reading.slots["tile"] == "wire"
        assert desk.show(shipped).reading.slots["tile"] == "wire"


def test_a_hand_resting_on_a_tile_for_longer_does_empty_its_slot(desk, shipped, tile_covered):
    # Known limit: a covered marker cannot be told from a tile taken away, so a hand that
    # stays for STABLE_FRAMES frames opens the circuit until it moves off again.
    desk.show(shipped, times=3)
    assert desk.show(tile_covered, times=STABLE_FRAMES).reading.slots["tile"] == "empty"
    assert desk.show(shipped, times=STABLE_FRAMES).reading.slots["tile"] == "wire"


def test_a_hand_on_one_slot_does_not_hold_up_a_change_elsewhere(desk, layout, shipped):
    # Each line and slot settles on its own, or a fidgeting hand would freeze the mat.
    drawn = Scene(layout).place_starting_tiles().draw_line("gap")
    drawn_and_covered = Scene(layout).place_starting_tiles().draw_line("gap").cover_slot("tile")
    desk.show(shipped, times=3)
    desk.show(drawn.photograph())
    desk.show(drawn_and_covered.photograph())
    assert desk.show(drawn.photograph()).reading.drawn == {"gap"}


def test_frames_with_a_hidden_corner_keep_the_last_reading(desk, shipped, corner_covered):
    before = desk.show(shipped, times=3).reading
    # The gap is drawn in these frames, but with a corner hidden the mat is not read.
    assert desk.show(corner_covered, times=10).reading == before


def test_a_hidden_corner_at_the_start_leaves_the_initial_reading(desk, layout, corner_covered):
    assert desk.show(corner_covered, times=4).reading == layout.initial_reading()


@pytest.mark.parametrize("view", [STRAIGHT, UPSIDE_DOWN])
def test_a_mat_turned_right_round_reads_the_same(view: View, desk, layout, geometry):
    scene = Scene(layout).place_tile("tile", "bulb").place_tile("side", "wire").draw_line("gap")
    # A finger on the middle of the tile slot.
    desk.finger.tip_px = frame_position(view, geometry.dot_mm((7, 2)))
    observation = desk.show(scene.photograph(view), times=3)
    assert observation.reading == MatReading(
        drawn=frozenset({"gap"}), slots={"tile": "bulb", "side": "wire"}
    )
    assert observation.fingertip.x == pytest.approx(7 / 8, abs=0.02)
    assert observation.fingertip.y == pytest.approx(2 / 5, abs=0.02)


def test_the_fingertip_is_reported_in_mat_position(desk, layout, geometry, shipped):
    for dot in [(0, 0), (8, 5), (4, 0), (1, 3)]:
        desk.finger.tip_px = frame_position(STRAIGHT, geometry.dot_mm(dot))
        fingertip = desk.show(shipped).fingertip
        assert fingertip.x == pytest.approx(dot[0] / (layout.cols - 1), abs=0.02)
        assert fingertip.y == pytest.approx(dot[1] / (layout.rows - 1), abs=0.02)


def test_there_is_no_fingertip_without_a_hand(desk, shipped):
    desk.finger.tip_px = None
    assert desk.show(shipped).fingertip is None


def test_there_is_no_fingertip_without_a_hand_tracker(layout, shipped):
    frames = ShownFrames()
    source = VisionSource(layout, frames)
    frames.show(shipped)
    assert source.observe().fingertip is None


def test_a_fingertip_off_the_mat_is_not_reported(desk, geometry, shipped):
    first_x_mm, first_y_mm = geometry.dot_mm((0, 0))
    # 0.4 of a dot (11 mm) outside the grid still counts; 0.6 of a dot (17 mm) does not.
    desk.finger.tip_px = frame_position(STRAIGHT, (first_x_mm - 11, first_y_mm - 11))
    assert desk.show(shipped).fingertip is not None
    desk.finger.tip_px = frame_position(STRAIGHT, (first_x_mm - 17, first_y_mm))
    assert desk.show(shipped).fingertip is None
    desk.finger.tip_px = frame_position(STRAIGHT, (first_x_mm, first_y_mm - 17))
    assert desk.show(shipped).fingertip is None
    desk.finger.tip_px = (1e9, -1e9)
    assert desk.show(shipped).fingertip is None


def test_there_is_no_fingertip_until_the_mat_has_been_found(desk, corner_covered):
    desk.finger.tip_px = (960.0, 540.0)
    assert desk.show(corner_covered).fingertip is None


def test_the_fingertip_is_still_placed_while_a_hand_hides_a_corner(
    desk, geometry, shipped, corner_covered
):
    desk.show(shipped)
    dot_mm = geometry.dot_mm((4, 4))
    desk.finger.tip_px = frame_position(STRAIGHT, dot_mm)
    fingertip = desk.show(corner_covered).fingertip
    assert (fingertip.x, fingertip.y) == pytest.approx((4 / 8, 4 / 5), abs=0.02)


def test_each_frame_is_processed_once_however_often_it_is_observed(desk, shipped, gap_drawn):
    desk.show(shipped, times=3)
    desk.frames.show(gap_drawn)
    seen_before = desk.finger.frames_seen
    observations = [desk.source.observe() for _ in range(50)]
    assert desk.finger.frames_seen == seen_before + 1
    # Fifty looks at one frame are one sighting of the change, not three.
    assert all(observation.reading.drawn == frozenset() for observation in observations)


def test_observing_with_no_new_frame_takes_under_a_millisecond(desk, shipped):
    desk.show(shipped, times=3)
    calls = 2000
    started = time.perf_counter()
    for _ in range(calls):
        desk.source.observe()
    assert (time.perf_counter() - started) / calls < 0.001


def test_frames_that_are_not_pictures_of_the_mat_do_not_raise(desk, layout, shipped):
    desk.finger.tip_px = (3.0, 3.0)
    before = desk.show(shipped, times=3).reading
    for odd in (
        np.zeros((1080, 1920, 3), np.uint8),
        np.zeros((1, 1, 3), np.uint8),
        np.zeros((0, 0, 3), np.uint8),
        np.zeros((480, 640), np.uint8),
        np.zeros((480, 640, 4), np.uint8),
        np.zeros((480, 640, 3), np.float64),
    ):
        assert desk.show(odd, times=4).reading == before


def test_greyscale_and_alpha_frames_of_the_mat_are_read(desk, layout, gap_drawn):
    grey = cv2.cvtColor(gap_drawn, cv2.COLOR_BGR2GRAY)
    assert desk.show(grey, times=3).reading.drawn == {"gap"}
    other = Desk(layout)
    with_alpha = cv2.cvtColor(gap_drawn, cv2.COLOR_BGR2BGRA)
    assert other.show(with_alpha, times=3).reading.drawn == {"gap"}


def test_in_the_background_frames_are_processed_off_the_callers_thread(layout, gap_drawn):
    class LiveCamera:
        def latest_frame(self) -> np.ndarray:
            return gap_drawn.copy()

    finger = PointingFinger()
    source = VisionSource(layout, LiveCamera(), finger)
    source.start()
    try:
        deadline = time.monotonic() + 10
        while source.observe().reading.drawn != {"gap"} and time.monotonic() < deadline:
            time.sleep(0.01)
        assert source.observe().reading.drawn == {"gap"}
        # observe() itself did none of the work: it never waits on a frame.
        seen = finger.frames_seen
        started = time.perf_counter()
        for _ in range(200):
            source.observe()
        assert (time.perf_counter() - started) / 200 < 0.001
        assert seen >= STABLE_FRAMES
    finally:
        source.stop()
    seen_when_stopped = finger.frames_seen
    time.sleep(0.05)
    assert finger.frames_seen == seen_when_stopped


def test_folder_frames_loops_through_image_files_in_name_order(tmp_path):
    for name, shade in [("b.png", 20), ("a.png", 10), ("c.jpg", 30)]:
        cv2.imwrite(str(tmp_path / name), np.full((40, 40, 3), shade, np.uint8))
    (tmp_path / "notes.txt").write_text("not a frame")
    (tmp_path / "broken.png").write_bytes(b"not a png")
    frames = FolderFrames(tmp_path)
    shades = [round(float(frames.latest_frame().mean()), -1) for _ in range(7)]
    assert shades == [10, 20, 30, 10, 20, 30, 10]


def test_folder_frames_gives_nothing_for_an_empty_or_missing_folder(tmp_path):
    assert FolderFrames(tmp_path).latest_frame() is None
    assert FolderFrames(tmp_path / "missing").latest_frame() is None
    (tmp_path / "broken.png").write_bytes(b"not a png")
    assert FolderFrames(tmp_path).latest_frame() is None


def test_recorded_frames_replay_into_readings(tmp_path, layout, shipped, gap_drawn):
    for index in range(3):
        cv2.imwrite(str(tmp_path / f"frame-{index}.png"), gap_drawn)
    source = VisionSource(layout, FolderFrames(tmp_path))
    readings = [source.observe().reading for _ in range(3)]
    assert [reading.drawn for reading in readings] == [frozenset(), frozenset(), {"gap"}]
