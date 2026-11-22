"""The lab: what is on the mat in, one `State` message out.

A `MatSource` says which pieces lie where and where the fingertip is: the camera, or
recorded frames. The lab solves the circuit, works out what the finger is touching,
and keeps the battery voltage the browser asks for.

A switch is open or closed as the source reports it: open and closed switches are
different printed pieces, and the learner swaps one for the other.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from threading import RLock
from typing import Protocol, TypeVar

from tacto.contract import (
    Circuit,
    ClientMessage,
    ContinueLesson,
    Dot,
    Grid,
    LessonStep,
    Piece,
    RestartLesson,
    SetMode,
    Source,
    State,
    Touch,
)
from tacto.lesson import LessonRunner
from tacto.pieces import Placed, solve_pieces, touch_for

# The wheel step raises this to 6 V, leaving room for the final parallel comparison.
DEFAULT_VOLTS = 3.0
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
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._grid = grid
        self._lock = RLock()
        self._mode = "tinker"
        self._source = source
        self._source_name: Source = source_name
        self._now = now
        self._started = now()
        self._volts = DEFAULT_VOLTS
        self._seq = 0
        self._lesson = lesson
        self._solved_for: tuple[tuple[Placed, ...], float] | None = None
        self._solved: tuple[list[Piece], Circuit] = ([], Circuit())

    def handle(self, message: ClientMessage) -> None:
        # State is solved on a worker thread; a mode change/reset must be atomic with it.
        with self._lock:
            if isinstance(message, RestartLesson):
                self.restart_lesson()
            elif isinstance(message, SetMode):
                if message.mode == "lab" and self._mode != "lab":
                    self.restart_lesson()
                self._mode = message.mode
            elif isinstance(message, ContinueLesson):
                if self._mode == "lab" and self._lesson is not None:
                    self._lesson.continue_step(message.step_id)
            else:
                self._volts = message.volts

    def restart_lesson(self) -> None:
        with self._lock:
            self._mode = "lab"
            self._volts = DEFAULT_VOLTS
            if self._lesson is not None:
                self._lesson.restart()

    def state(self) -> State:
        with self._lock:
            return self._state()

    def _state(self) -> State:
        view = self._source.view()
        now = self._now()
        pieces, circuit = self._solve(view.placed)
        touch = self._touch(view, pieces)
        state = State(
            seq=self._seq,
            t=round(now - self._started, 3),
            source=self._source_name,
            mode=self._mode,
            mat_visible=view.mat_visible,
            grid=self._grid,
            pieces=pieces,
            circuit=circuit,
            touch=touch,
            lesson=(
                self._lesson.update(pieces, circuit, touch, mat_visible=view.mat_visible)
                if self._lesson and self._mode == "lab"
                else LessonStep()
            ),
        )
        self._seq += 1
        return state

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
