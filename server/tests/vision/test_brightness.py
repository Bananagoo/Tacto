"""Automatic brightness: the camera's gain is steered so the paper sits near a target."""

import pytest

from tacto.vision.brightness import (
    MAX_GAIN,
    PERIOD_S,
    TARGET_PAPER,
    AutoGain,
    paper_level,
)


class Camera:
    """A stand-in camera: paper brightness rises about 2 per gain step from a base level."""

    def __init__(self, base: float, gain: int = 0) -> None:
        self.base, self.gain, self.set_to = base, gain, []

    def apply(self, gain: int) -> bool:
        self.set_to.append(gain)
        self.gain = gain
        return True

    @property
    def paper(self) -> float:
        return min(255.0, self.base + 2.1 * self.gain)

    @property
    def clipped(self) -> float:
        return 0.9 if self.paper >= 252 else 0.0


def run(camera: Camera, seconds: float = 15.0, start_gain: int = 0) -> AutoGain:
    clock = [0.0]
    auto = AutoGain(camera.apply, start_gain=start_gain, clock=lambda: clock[0])
    for _ in range(round(seconds * 20)):
        clock[0] += 0.05
        auto.saw(camera.paper, camera.clipped)
    return auto


def test_a_dim_room_is_brightened_until_the_paper_is_near_the_target():
    camera = Camera(base=120)
    auto = run(camera)
    assert abs(camera.paper - TARGET_PAPER) <= 12 and auto.state == "settled"


def test_the_desk_it_was_tuned_on_is_brightened_a_little():
    camera = Camera(base=181)  # gain 0 on Katie's desk, 22 Nov 2026
    run(camera)
    assert abs(camera.paper - TARGET_PAPER) <= 12 and 0 < camera.gain < 20


def test_a_bright_room_is_turned_down_from_a_high_start():
    camera = Camera(base=150, gain=40)
    run(camera, start_gain=40)
    assert abs(camera.paper - TARGET_PAPER) <= 12


def test_clipping_paper_is_backed_off_at_once():
    camera = Camera(base=200, gain=30)  # paper at 255: clipped
    run(camera, seconds=3, start_gain=30)
    assert camera.paper < 252


def test_it_never_goes_past_its_limits_and_says_so():
    dark = Camera(base=20)
    auto = run(dark)
    assert dark.gain == MAX_GAIN and auto.state == "too dark"
    glaring = Camera(base=245)
    auto = run(glaring)
    assert glaring.gain == 0 and auto.state == "too bright"


def test_it_changes_the_camera_at_most_once_a_period():
    camera = Camera(base=100)
    clock = [0.0]
    auto = AutoGain(camera.apply, clock=lambda: clock[0])
    for _ in range(int(PERIOD_S / 0.05) - 1):
        clock[0] += 0.05
        auto.saw(camera.paper, camera.clipped)
    assert len(camera.set_to) <= 1


def test_settled_means_left_alone():
    camera = Camera(base=TARGET_PAPER)
    auto = run(camera)
    assert camera.set_to == [] and auto.state == "settled"


def test_no_paper_reading_changes_nothing():
    camera = Camera(base=100)
    clock = [0.0]
    auto = AutoGain(camera.apply, clock=lambda: clock[0])
    for _ in range(100):
        clock[0] += 0.05
        auto.saw(None, None)
    assert camera.set_to == [] and auto.state == "waiting"


def test_a_camera_that_cannot_be_set_is_not_retried_every_frame():
    tries = []
    clock = [0.0]
    auto = AutoGain(lambda gain: tries.append(gain) or False, clock=lambda: clock[0])
    for _ in range(200):
        clock[0] += 0.05
        auto.saw(100.0, 0.0)
    assert len(tries) <= 2 and auto.state == "unavailable"


def test_paper_level_is_the_paper_and_clipping_is_counted():
    import numpy as np

    page = np.full((210, 297, 3), 190, np.uint8)
    page[:20, :30] = (30, 30, 200)  # a piece
    level, clipped = paper_level(page)
    assert level == pytest.approx(190, abs=1) and clipped == 0.0
    page[:, :100] = 255
    assert paper_level(page)[1] == pytest.approx(100 / 297, abs=0.02)


# ---------- calibrate, then hold still (22 Nov 2026) ----------
# Live, the gain kept moving: with a glare spot on the mat the paper read dim (so up) and the
# spot clipped (so down), every 0.4 s, and each change shifted every colour the reader saw.


class GlareCamera(Camera):
    """Dim paper with a shiny spot that clips once the gain reaches 20, whatever the paper."""

    @property
    def clipped(self) -> float:
        return 0.03 if self.gain >= 20 else 0.0


def test_a_glare_spot_does_not_make_it_swing_up_and_down():
    camera = GlareCamera(base=140)  # the paper alone would want gain 29
    auto = run(camera, seconds=30)
    assert camera.gain < 20  # never left clipping
    assert len(camera.set_to) <= 10  # closed in and stopped, no back and forth
    assert auto.state == "glare" and auto.locked


def test_once_calibrated_a_shadow_or_a_hand_changes_nothing():
    camera = Camera(base=120)
    auto = run(camera)
    assert auto.locked
    settled_at = list(camera.set_to)
    clock = [100.0]
    auto._clock = lambda: clock[0]  # noqa: SLF001 - the same controller, later
    for paper in (90.0, 60.0, 240.0, 120.0) * 20:  # a hand, a shadow, a lamp, ...
        clock[0] += 0.05
        auto.saw(paper, 0.0)
    assert camera.set_to == settled_at


def test_recalibrating_unlocks_it_for_the_new_light():
    camera = Camera(base=120)
    clock = [0.0]
    auto = AutoGain(camera.apply, clock=lambda: clock[0])

    def look(seconds):
        for _ in range(round(seconds * 20)):
            clock[0] += 0.05
            auto.saw(camera.paper, camera.clipped)

    look(15)
    assert auto.locked
    camera.base = 140  # the room got brighter
    look(5)
    assert abs(camera.paper - TARGET_PAPER) > 12  # held: nobody asked
    auto.recalibrate()
    assert not auto.locked
    look(15)
    assert abs(camera.paper - TARGET_PAPER) <= 12 and auto.locked


def test_calibration_gives_up_and_holds_after_its_time_limit():
    # A paper reading that wanders forever must still end in a held setting.
    camera = Camera(base=120)
    clock = [0.0]
    auto = AutoGain(camera.apply, clock=lambda: clock[0])
    for i in range(400):
        clock[0] += 0.05
        auto.saw(150.0 if i % 2 else 250.0, 0.0)
    assert auto.locked
