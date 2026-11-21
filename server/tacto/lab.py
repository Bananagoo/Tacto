"""The lab: what is on the mat in, one `State` message out.

A `MatSource` says which pieces lie where and where the fingertip is. The camera
is one source; a mat set by hand is another. The lab solves the circuit, works
out what the finger is touching, and keeps the battery voltage the browser asks for.

The camera cannot see whether a paper switch is open or closed: the learner taps it.
So the lab remembers which switches have been tapped an odd number of times and
flips those relative to what the source reports. A switch that leaves the mat is
forgotten, so a new one starts as the source reports it (open, for the camera).
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol, TypeVar

from tacto.contract import (
    Circuit,
    Dot,
    Grid,
    LessonStep,
    Piece,
    SetVoltage,
    Source,
    State,
    Touch,
)
from tacto.lesson import LessonRunner
from tacto.pieces import Placed, solve_pieces, touch_for
from tacto.taps import SwitchTaps

DEFAULT_VOLTS = 6.0
# How far from a piece, in dot spacings, a fingertip still counts as on it.
# TODO(vision owner): tune on the real mat; hand tracking jitters by a few millimetres.
REACH_DOTS = 0.35


@dataclass(frozen=True)
class MatView:
    """One look at the mat."""

    placed: tuple[Placed, ...] = ()
    finger: tuple[float, float] | None = None  # 0..1 across the dot grid; None is no hand
    mat_visible: bool = True


class MatSource(Protocol):
    def view(self) -> MatView:
        """The latest look at the mat. Must be cheap: it is called for every message."""
        ...


class Lab:
    """Turns a mat source into state messages. One lab serves every connected browser."""

    def __init__(
        self,
        grid: Grid,
        source: MatSource,
        *,
        source_name: Source,
        lesson: LessonRunner | None = None,
        tap_switches: bool = True,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._grid = grid
        self._source = source
        self._source_name: Source = source_name
        self._now = now
        self._started = now()
        self._volts = DEFAULT_VOLTS
        self._seq = 0
        self._lesson = lesson
        # False for the camera: its switches are two printed pieces, open and closed, and
        # the reader says which one is down. A fingertip resting on one changes nothing.
        self._tap_switches = tap_switches
        self._taps = SwitchTaps()
        self._flipped: set[str] = set()
        self._solved_for: tuple[tuple[Placed, ...], float] | None = None
        self._solved: tuple[list[Piece], Circuit] = ([], Circuit())

    def handle(self, message: SetVoltage) -> None:
        self._volts = message.volts

    def restart_lesson(self) -> None:
        if self._lesson is not None:
            self._lesson.restart()

    def state(self) -> State:
        view = self._source.view()
        now = self._now()
        pieces, circuit = self._solve(self._with_taps(view, now))
        state = State(
            seq=self._seq,
            t=round(now - self._started, 3),
            source=self._source_name,
            mat_visible=view.mat_visible,
            grid=self._grid,
            pieces=pieces,
            circuit=circuit,
            touch=self._touch(view, pieces),
            lesson=self._lesson.update(pieces, circuit) if self._lesson else LessonStep(),
        )
        self._seq += 1
        return state

    def _with_taps(self, view: MatView, now: float) -> tuple[Placed, ...]:
        """The source's pieces, with every tapped switch flipped."""
        if not self._tap_switches:
            return view.placed
        switches = {p.id for p in view.placed if p.type == "switch"}
        if view.mat_visible:
            self._flipped &= switches
        under_finger = piece_at(view.placed, self._grid, *view.finger) if view.finger else None
        on_switch = under_finger.id if under_finger and under_finger.id in switches else None
        tapped = self._taps.update(on_switch, now)
        if tapped is not None:
            self._flipped ^= {tapped}
        return tuple(
            replace(p, closed=not p.closed) if p.id in self._flipped else p for p in view.placed
        )

    def _solve(self, placed: tuple[Placed, ...]) -> tuple[list[Piece], Circuit]:
        # The mat changes a few times a minute and the state goes out 15 times a
        # second, so solve only when the pieces or the voltage change.
        key = (placed, self._volts)
        if key != self._solved_for:
            self._solved = solve_pieces(placed, self._volts)
            self._solved_for = key
        return self._solved

    def _touch(self, view: MatView, pieces: Sequence[Piece]) -> Touch:
        if view.finger is None:
            return Touch()
        x, y = view.finger
        piece = piece_at(pieces, self._grid, x, y)
        return touch_for(pieces, x=x, y=y, piece_id=piece.id if piece else None)


class _OnSegment(Protocol):
    @property
    def a(self) -> Dot: ...
    @property
    def b(self) -> Dot: ...


SegmentT = TypeVar("SegmentT", bound=_OnSegment)


def piece_at(pieces: Sequence[SegmentT], grid: Grid, x: float, y: float) -> SegmentT | None:
    """The nearest piece within reach of mat position (x, y), or None."""
    point = (x * (grid.cols - 1), y * (grid.rows - 1))
    best: SegmentT | None = None
    best_distance = REACH_DOTS
    for piece in pieces:
        distance = _distance_to_segment(point, piece.a, piece.b)
        if distance < best_distance:
            best, best_distance = piece, distance
    return best


def _distance_to_segment(point: tuple[float, float], a: Dot, b: Dot) -> float:
    px, py = point
    dx, dy = b[0] - a[0], b[1] - a[1]
    # How far along the segment the closest point is, held between its two ends.
    along = max(0.0, min(1.0, (px - a[0]) * dx + (py - a[1]) * dy))
    return math.hypot(px - (a[0] + along * dx), py - (a[1] + along * dy))
