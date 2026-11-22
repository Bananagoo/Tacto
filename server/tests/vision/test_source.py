"""The camera source end to end on rendered frames: frames in, a MatView and a State out."""

import cv2
import numpy as np
from vision_scenes import TILTED, Scene, frame_position

from tacto.lab import Lab
from tacto.pieces import Placed
from tacto.vision.frames import FramesOnAClock
from tacto.vision.source import CameraMatSource
from tacto.vision.stable import FRAMES_TO_CHANGE


class NoFrames:
    def wait_for_frame(self, after, timeout):
        return None


class Hand:
    """A hand tracker that reports one hand with every point at the same frame pixel."""

    def __init__(self) -> None:
        self.at_px: tuple[float, float] | None = None

    def hands(self, frame, t_ms):
        if self.at_px is None:
            return []
        return [{"handedness": "Right", "points": [list(self.at_px)] * 21}]


def loop(mat) -> Scene:
    """A battery, a closed switch, a bulb and wires round one square: a working circuit."""
    return (
        Scene(mat, squares=True)
        .lay("battery", (2, 2), (3, 2), positive="a")
        .lay("bulb", (2, 3), (3, 3))
        .lay("wire", (2, 2), (2, 3))
        .lay("switch_closed", (3, 2), (3, 3))
    )


def feed(source: CameraMatSource, frame: np.ndarray, times: int = FRAMES_TO_CHANGE) -> None:
    for _ in range(times):
        source.step(frame)


def test_before_any_frame_the_mat_is_not_visible(mat):
    view = CameraMatSource(mat, NoFrames()).view()
    assert view.mat_visible is False and view.placed == () and view.finger is None


def test_pieces_appear_after_enough_frames_with_polarity_and_switch_state(mat):
    source = CameraMatSource(mat, NoFrames())
    frame = loop(mat).photograph(TILTED)
    feed(source, frame, FRAMES_TO_CHANGE - 1)
    assert source.view().mat_visible is True and source.view().placed == ()
    feed(source, frame, 1)
    assert set(source.view().placed) == {
        Placed("battery", (2, 2), (3, 2)),
        Placed("bulb", (2, 3), (3, 3)),
        Placed("wire", (2, 2), (2, 3)),
        Placed("switch", (3, 2), (3, 3), closed=True),
    }


def test_the_lab_turns_the_camera_view_into_a_working_circuit(mat):
    source = CameraMatSource(mat, NoFrames())
    feed(source, loop(mat).photograph(TILTED))
    state = Lab(mat.grid, source, source_name="camera").state()
    assert state.mat_visible is True and state.circuit.status == "working"
    bulb = next(p for p in state.pieces if p.type == "bulb")
    assert bulb.brightness > 0 and abs(bulb.current) > 0


def test_swapping_the_closed_switch_for_the_open_one_opens_the_circuit(mat):
    source = CameraMatSource(mat, NoFrames())
    lab = Lab(mat.grid, source, source_name="camera")
    feed(source, loop(mat).photograph(TILTED))
    assert lab.state().circuit.status == "working"
    opened = (
        Scene(mat, squares=True)
        .lay("battery", (2, 2), (3, 2), positive="a")
        .lay("bulb", (2, 3), (3, 3))
        .lay("wire", (2, 2), (2, 3))
        .lay("switch_open", (3, 2), (3, 3))
    )
    feed(source, opened.photograph(TILTED))
    state = lab.state()
    assert state.circuit.status == "open"
    assert next(p for p in state.pieces if p.type == "switch").closed is False


def test_a_finger_resting_on_a_switch_does_not_toggle_it(mat):
    clock = [0.0]
    hand = Hand()
    source = CameraMatSource(mat, NoFrames(), hands=hand, clock=lambda: clock[0])
    lab = Lab(mat.grid, source, source_name="camera", now=lambda: clock[0])
    frame = loop(mat).photograph(TILTED)
    feed(source, frame)
    geometry = source._geometry
    middle = tuple(np.mean([geometry.dot_mm((3, 2)), geometry.dot_mm((3, 3))], axis=0))
    hand.at_px = frame_position(TILTED, middle)
    for _ in range(30):
        clock[0] += 0.1
        source.step(frame)
        state = lab.state()
    assert state.touch.present and state.touch.piece_id == "3,2-3,3"
    assert next(p for p in state.pieces if p.type == "switch").closed is True


def test_the_fingertip_is_reported_on_the_mat_and_touches_the_piece_under_it(mat):
    hand = Hand()
    source = CameraMatSource(mat, NoFrames(), hands=hand)
    frame = loop(mat).photograph(TILTED)
    feed(source, frame)
    geometry = source._geometry
    middle = tuple(np.mean([geometry.dot_mm((2, 3)), geometry.dot_mm((3, 3))], axis=0))
    hand.at_px = frame_position(TILTED, middle)
    source.step(frame)
    x, y = source.view().finger
    assert abs(x - 2.5 / 8) < 0.02 and abs(y - 3 / 5) < 0.02
    state = Lab(mat.grid, source, source_name="camera").state()
    assert state.touch.piece_id == "2,3-3,3" and state.touch.pulse_hz > 0


def test_a_hand_off_the_mat_is_no_fingertip(mat):
    hand = Hand()
    source = CameraMatSource(mat, NoFrames(), hands=hand)
    frame = loop(mat).photograph(TILTED)
    hand.at_px = (5.0, 5.0)  # the far corner of the frame, on the desk
    feed(source, frame)
    assert source.view().finger is None and len(source.view().placed) == 4


def test_a_piece_under_the_hand_holds_while_it_is_hidden(mat):
    # Changed 22 Nov 2026: what a hand covered now stays covered for half a second after
    # the hand is last seen, so this test runs on its own clock and waits that out.
    clock = [0.0]
    hand = Hand()
    source = CameraMatSource(mat, NoFrames(), hands=hand, clock=lambda: clock[0])
    feed(source, loop(mat).photograph(TILTED))
    geometry = source._geometry
    middle = tuple(np.mean([geometry.dot_mm((2, 3)), geometry.dot_mm((3, 3))], axis=0))
    # The same mat with the bulb gone, as it looks to the reader while a hand hides it.
    hidden = (
        Scene(mat, squares=True)
        .lay("battery", (2, 2), (3, 2), positive="a")
        .lay("wire", (2, 2), (2, 3))
        .lay("switch_closed", (3, 2), (3, 3))
    )
    hand.at_px = frame_position(TILTED, middle)
    feed(source, hidden.photograph(TILTED), 20)
    assert Placed("bulb", (2, 3), (3, 3)) in source.view().placed
    hand.at_px = None
    for _ in range(24):
        clock[0] += 1 / 24
        source.step(hidden.photograph(TILTED))
    assert Placed("bulb", (2, 3), (3, 3)) not in source.view().placed


def test_a_soft_frame_changes_nothing_and_the_mat_stays_visible(mat):
    source = CameraMatSource(mat, NoFrames())
    feed(source, loop(mat).photograph(TILTED))
    before = source.view().placed
    soft = cv2.GaussianBlur(Scene(mat, squares=True).photograph(TILTED), (0, 0), 12)
    feed(source, soft, 10)  # an empty mat, but too blurred to trust
    assert source.view().mat_visible is True and source.view().placed == before


def test_a_frame_with_no_mat_reports_it_gone_and_keeps_the_pieces(mat):
    source = CameraMatSource(mat, NoFrames())
    feed(source, loop(mat).photograph(TILTED))
    # Never seen and never found: a different source, a bare desk.
    bare = CameraMatSource(mat, NoFrames())
    feed(bare, np.full((1080, 1920, 3), 90, np.uint8))
    assert bare.view().mat_visible is False
    assert len(source.view().placed) == 4


def test_the_reader_thread_takes_frames_from_a_folder_like_a_camera(mat, tmp_path):
    cv2.imwrite(str(tmp_path / "00000.png"), loop(mat).photograph(TILTED))
    from tacto.vision.frames import FolderFrames

    source = CameraMatSource(mat, FramesOnAClock(FolderFrames(tmp_path), fps=200))
    source.start()
    try:
        import time

        deadline = time.time() + 10
        while len(source.view().placed) < 4 and time.time() < deadline:
            time.sleep(0.02)
    finally:
        source.stop()
    assert len(source.view().placed) == 4
    report = source.report()
    assert report["frames"] >= FRAMES_TO_CHANGE and report["squares_seen"] == 7
    assert set(report["stage_ms"]) == {"flatten", "read", "smooth"}


# ---------- a whole hand and arm, not twenty-one points ----------


class RealHand:
    """A hand tracker reporting a right hand lying flat on the page, fingers pointing up
    the page, with its wrist at `wrist_mm`. None is no hand. Shaped like a real one: about
    80 mm across the knuckles and 180 mm from wrist to middle fingertip."""

    # Millimetres from the wrist: (across, towards the fingertips), per MediaPipe point.
    SHAPE = [
        (0, 0), (-30, 25), (-48, 50), (-58, 75), (-65, 95),  # wrist, thumb
        (-28, 95), (-30, 130), (-31, 152), (-32, 170),  # index
        (-5, 100), (-5, 138), (-5, 162), (-5, 182),  # middle
        (16, 95), (18, 130), (19, 152), (20, 168),  # ring
        (36, 85), (40, 112), (42, 130), (44, 145),  # little
    ]  # fmt: skip

    def __init__(self) -> None:
        self.wrist_mm: tuple[float, float] | None = None

    def hands(self, frame, t_ms):
        if self.wrist_mm is None:
            return []
        x, y = self.wrist_mm
        points = [list(frame_position(TILTED, (x + dx, y - dy))) for dx, dy in self.SHAPE]
        return [{"handedness": "Right", "points": points}]


def without_the_bulb(mat) -> Scene:
    return (
        Scene(mat, squares=True)
        .lay("battery", (2, 2), (3, 2), positive="a")
        .lay("wire", (2, 2), (2, 3))
        .lay("switch_closed", (3, 2), (3, 3))
    )


BULB = Placed("bulb", (2, 3), (3, 3))  # its middle is at (106.5, 119) mm on the page


def test_a_piece_under_the_palm_holds_though_no_joint_is_near_it(mat):
    hand = RealHand()
    source = CameraMatSource(mat, NoFrames(), hands=hand)
    feed(source, loop(mat).photograph(TILTED))
    # The bulb's middle is 50 mm up from the wrist, in the middle of the palm: over 25 mm
    # from the wrist, the thumb's base and every knuckle.
    hand.wrist_mm = (106.5, 169.0)
    feed(source, without_the_bulb(mat).photograph(TILTED), 30)
    assert BULB in source.view().placed


def test_a_piece_under_the_forearm_holds(mat):
    hand = RealHand()
    source = CameraMatSource(mat, NoFrames(), hands=hand)
    feed(source, loop(mat).photograph(TILTED))
    # The hand is reaching past the bulb: the wrist is 60 mm beyond it, towards the top of
    # the page, so the bulb lies under the arm.
    hand.wrist_mm = (106.5, 59.0)
    feed(source, without_the_bulb(mat).photograph(TILTED), 30)
    assert BULB in source.view().placed


def test_a_hand_lost_for_a_few_frames_still_covers_what_it_covered(mat):
    clock = [0.0]
    hand = RealHand()
    source = CameraMatSource(mat, NoFrames(), hands=hand, clock=lambda: clock[0])
    feed(source, loop(mat).photograph(TILTED))
    hidden = without_the_bulb(mat).photograph(TILTED)
    for frame in range(60):
        clock[0] += 1 / 24
        # A moving hand: the tracker loses it for five frames in every eight.
        hand.wrist_mm = (106.5, 169.0) if frame % 8 < 3 else None
        source.step(hidden)
    assert BULB in source.view().placed


def test_once_the_hand_has_gone_the_mat_is_read_again(mat):
    clock = [0.0]
    hand = RealHand()
    source = CameraMatSource(mat, NoFrames(), hands=hand, clock=lambda: clock[0])
    feed(source, loop(mat).photograph(TILTED))
    hidden = without_the_bulb(mat).photograph(TILTED)
    hand.wrist_mm = (106.5, 169.0)
    for _ in range(10):
        clock[0] += 1 / 24
        source.step(hidden)
    hand.wrist_mm = None
    for _ in range(40):
        clock[0] += 1 / 24
        source.step(hidden)
    assert BULB not in source.view().placed


def test_a_piece_laid_far_from_the_hand_still_appears_while_the_hand_is_there(mat):
    clock = [0.0]
    hand = RealHand()
    source = CameraMatSource(mat, NoFrames(), hands=hand, clock=lambda: clock[0])
    hand.wrist_mm = (106.5, 169.0)
    frame = loop(mat).lay("resistor", (6, 1), (7, 1)).photograph(TILTED)
    for _ in range(24):
        clock[0] += 1 / 24
        source.step(frame)
    assert Placed("resistor", (6, 1), (7, 1)) in source.view().placed
