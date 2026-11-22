"""Smoothing the fingertip: steady when the finger rests, quick when it moves."""

import random
import statistics

import pytest

from tacto.vision.fingertip import FingertipSmoother

FRAME_S = 1 / 30


def run(points, start=0.0):
    smoother = FingertipSmoother()
    out = []
    t = start
    for point in points:
        out.append(smoother.smooth(point, t))
        t += FRAME_S
    return smoother, out


def test_a_resting_finger_jitters_far_less():
    # MediaPipe's tip wanders a millimetre or two a frame: about 0.006 of the mat here.
    noise = random.Random(7)
    raw = [(0.5 + noise.gauss(0, 0.006), 0.4 + noise.gauss(0, 0.006)) for _ in range(90)]
    _, out = run(raw)
    settled = out[30:]
    raw_spread = statistics.pstdev([x for x, _ in raw[30:]])
    out_spread = statistics.pstdev([x for x, _ in settled])
    assert out_spread < raw_spread / 3


def test_a_moving_finger_is_followed_closely():
    # Sliding across a quarter of the mat in half a second, then resting.
    path = [(0.2 + 0.25 * min(1.0, i / 15), 0.5) for i in range(40)]
    _, out = run(path)
    assert out[-1][0] == pytest.approx(0.45, abs=0.01)
    # Not lagging far behind while moving: within 4% of the mat a few frames into the slide.
    assert abs(out[12][0] - path[12][0]) < 0.04


def test_a_finger_that_leaves_and_comes_back_elsewhere_jumps_there():
    smoother = FingertipSmoother()
    smoother.smooth((0.1, 0.1), 0.0)
    smoother.smooth((0.1, 0.1), 0.03)
    assert smoother.smooth(None, 0.06) is None
    assert smoother.smooth((0.8, 0.8), 0.5) == pytest.approx((0.8, 0.8))
