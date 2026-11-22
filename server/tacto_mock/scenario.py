"""The scripted run behind `contract/sample-states.jsonl`.

One learner follows the six-step demo, including the three spoken reflections.
The numbers come from the real solver and progress comes from the real lesson runner.

    (1,1)--w--(2,1)--BULB A--(3,1)--w--(4,1)
      |         :              :         |
     BAT+      (2,2). branch .(3,2)    SWITCH
      |                                  |
    (1,2)                              (4,2)
      |w                                 |w
    (1,3)--w--(2,3)--bottom--(3,3)--w--(4,3)
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from tacto.contract import Grid, PieceType, State, Touch, segment_id
from tacto.lesson import LessonRunner, load_lesson
from tacto.pieces import Placed, solve_pieces, touch_for

GRID = Grid(cols=9, rows=6)
FRAMES_PER_SECOND = 15
LESSON_FILE = Path(__file__).resolve().parents[2] / "lessons" / "circuits-101-full.yaml"

BATTERY = segment_id((1, 1), (1, 2))
BULB_A = segment_id((2, 1), (3, 1))
SWITCH = segment_id((4, 1), (4, 2))
BOTTOM = segment_id((2, 3), (3, 3))
BRANCH = segment_id((2, 2), (3, 2))
BATTERY_WIRE = segment_id((1, 1), (2, 1))
RIGHT_WIRE = segment_id((4, 2), (4, 3))


def loop(*, closed: bool, bottom: PieceType = "wire") -> list[Placed]:
    return [
        Placed("battery", (1, 1), (1, 2)),
        Placed("wire", (1, 1), (2, 1)),
        Placed("bulb", (2, 1), (3, 1)),
        Placed("wire", (3, 1), (4, 1)),
        Placed("switch", (4, 1), (4, 2), closed=closed),
        Placed("wire", (4, 2), (4, 3)),
        Placed("wire", (4, 3), (3, 3)),
        Placed(bottom, (3, 3), (2, 3)),
        Placed("wire", (2, 3), (1, 3)),
        Placed("wire", (1, 3), (1, 2)),
    ]


def branch(middle: PieceType) -> list[Placed]:
    return [
        Placed("wire", (2, 1), (2, 2)),
        Placed(middle, (2, 2), (3, 2)),
        Placed("wire", (3, 2), (3, 1)),
    ]


@dataclass(frozen=True)
class Beat:
    """A stretch of the run during which nothing on the mat changes."""

    seconds: float
    placed: tuple[Placed, ...]
    volts: float = 3.0
    finger_on: str | None = None
    mat_visible: bool = True
    continue_after: bool = False


def beats() -> list[Beat]:
    open_loop = tuple(loop(closed=False))
    one_bulb = tuple(loop(closed=True))
    series = tuple(loop(closed=True, bottom="bulb"))
    parallel = tuple(loop(closed=True) + branch("bulb"))
    return [
        Beat(2, ()),
        Beat(2, tuple(p for p in open_loop if p.type != "switch")),
        Beat(6, open_loop),
        Beat(2, open_loop),
        Beat(8, one_bulb),
        Beat(2, one_bulb),
        Beat(8, one_bulb, finger_on=BULB_A),
        Beat(3, one_bulb, finger_on=BULB_A),
        *(Beat(0.5, one_bulb, volts=v, finger_on=BULB_A) for v in (3.5, 4, 4.5, 5, 5.5, 6)),
        Beat(9, one_bulb, volts=6, finger_on=BULB_A, continue_after=True),
        Beat(3, one_bulb, volts=6),
        Beat(1, series, volts=6, mat_visible=False),
        Beat(2, series, volts=6),
        Beat(9, series, volts=6, finger_on=BULB_A, continue_after=True),
        Beat(4, one_bulb, volts=6),
        Beat(3, parallel, volts=6),
        Beat(5, parallel, volts=6, finger_on=BULB_A),
        Beat(13, parallel, volts=6, finger_on=BATTERY, continue_after=True),
        Beat(5, parallel, volts=6, finger_on=BATTERY),
    ]


def states() -> Iterator[State]:
    """A complete run with real half-second goals, linger times and reflection pauses."""
    seq = 0
    lesson = LessonRunner(load_lesson(LESSON_FILE), now=lambda: seq / FRAMES_PER_SECOND)
    for beat in beats():
        pieces, circuit = solve_pieces(beat.placed, beat.volts)
        touch = _touch(beat, pieces)
        for _ in range(round(beat.seconds * FRAMES_PER_SECOND)):
            report = lesson.update(pieces, circuit, touch, mat_visible=beat.mat_visible)
            yield State(
                seq=seq,
                t=round(seq / FRAMES_PER_SECOND, 3),
                source="replay",
                mode="lab",
                mat_visible=beat.mat_visible,
                grid=GRID,
                pieces=pieces,
                circuit=circuit,
                touch=touch,
                lesson=report,
            )
            seq += 1
        if beat.continue_after:
            lesson.continue_step(report.step_id)


def _touch(beat: Beat, pieces: list) -> Touch:
    piece = next((p for p in pieces if p.id == beat.finger_on), None)
    if piece is None:
        return Touch()
    x = (piece.a[0] + piece.b[0]) / 2 / (GRID.cols - 1)
    y = (piece.a[1] + piece.b[1]) / 2 / (GRID.rows - 1)
    return touch_for(pieces, x=round(x, 3), y=round(y, 3), piece_id=piece.id)
