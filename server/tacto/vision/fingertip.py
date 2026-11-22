"""Steadying the fingertip.

MediaPipe's fingertip wanders a millimetre or two from frame to frame even when the finger is
still, so the circle on screen shook and the touched piece could flicker at a piece's edge.
This is the One Euro filter (Casiez, Roussel and Vogel, CHI 2012), the usual smoother for
tracked points: a low-pass filter whose cut-off rises with the speed, so a resting finger is
smoothed hard and a moving one is followed with little lag. Positions are mat units (0 to 1
across the dot grid).
"""

from __future__ import annotations

import math

# TODO(Katie): tune by eye on the real mat. Lower MIN_CUTOFF_HZ: steadier at rest, more lag on
# the first move. Higher SPEED_GAIN: less lag when moving, more shake while moving.
MIN_CUTOFF_HZ = 1.2
SPEED_GAIN = 12.0
SPEED_CUTOFF_HZ = 1.0
# A gap this long (the finger left, or a frame was missed) starts afresh where it reappears.
GAP_S = 0.25


def _alpha(cutoff_hz: float, dt: float) -> float:
    tau = 1.0 / (2 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + tau / dt)


class _Axis:
    def __init__(self, value: float) -> None:
        self.value = value
        self.speed = 0.0

    def update(self, raw: float, dt: float) -> float:
        speed = (raw - self.value) / dt
        a_speed = _alpha(SPEED_CUTOFF_HZ, dt)
        self.speed = a_speed * speed + (1 - a_speed) * self.speed
        cutoff = MIN_CUTOFF_HZ + SPEED_GAIN * abs(self.speed)
        a = _alpha(cutoff, dt)
        self.value = a * raw + (1 - a) * self.value
        return self.value


class FingertipSmoother:
    """Give it each frame's fingertip (or None) and the time; it gives back the steadied one."""

    def __init__(self) -> None:
        self._axes: tuple[_Axis, _Axis] | None = None
        self._last_s: float | None = None

    def smooth(self, tip: tuple[float, float] | None, now_s: float) -> tuple[float, float] | None:
        if tip is None:
            self._axes = None
            return None
        dt = None if self._last_s is None else now_s - self._last_s
        self._last_s = now_s
        if self._axes is None or dt is None or dt <= 0 or dt > GAP_S:
            self._axes = (_Axis(tip[0]), _Axis(tip[1]))
            return tip
        x, y = self._axes
        return (x.update(tip[0], dt), y.update(tip[1], dt))
