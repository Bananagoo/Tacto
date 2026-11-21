"""The scripted run behind `contract/sample-states.jsonl`.

One learner walks through every state the lab can be in: an empty mat, an open
loop, a working loop, the voltage going up, series, parallel, a short, the mat
hidden from the camera, and a resistor. The numbers come from the real solver.

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

from tacto.contract_v2 import Grid, LessonStep, PieceType, State, Touch, segment_id
from tacto.pieces import Placed, solve_pieces, touch_for

GRID = Grid(cols=9, rows=6)
FRAMES_PER_SECOND = 15
LESSON_ID = "circuits-101"
# Placeholder wording; the lesson's real prompts belong to its author.
STEPS: tuple[tuple[str, str], ...] = (
    ("build", "Lay out the loop: battery, wires, bulb and switch."),
    ("close_the_loop", "Tap the switch to close the loop. Touch the bulb and feel the current."),
    ("series", "Swap the bottom wire for a second bulb."),
    ("parallel", "Move the second bulb to the branch beside the first."),
    ("short", "Swap the branch bulb for a wire."),
)

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
    step: int
    step_done: bool = False
    volts: float = 6.0
    finger_on: str | None = None  # a piece id; None means no hand over the mat
    mat_visible: bool = True
    lesson_done: bool = False


def beats() -> list[Beat]:
    open_loop = tuple(loop(closed=False))
    one_bulb = tuple(loop(closed=True))
    series = tuple(loop(closed=True, bottom="bulb"))
    parallel = tuple(loop(closed=True) + branch("bulb"))
    short = tuple(loop(closed=True) + branch("wire"))
    with_resistor = tuple(loop(closed=True, bottom="resistor"))
    return [
        # Step 0: the mat fills up piece by piece. Nothing flows.
        Beat(1.0, (), step=0),
        Beat(0.6, open_loop[:3], step=0),
        Beat(0.6, open_loop[:7], step=0),
        Beat(1.2, open_loop, step=0, step_done=True),
        # Step 1: a tap closes the switch; 6 V over 10 ohms is 0.6 A, a 3 Hz pulse.
        Beat(0.8, open_loop, step=1, finger_on=SWITCH),
        Beat(1.0, one_bulb, step=1, step_done=True, finger_on=SWITCH),
        Beat(1.5, one_bulb, step=1, step_done=True, finger_on=BULB_A),
        # The wheel takes the battery from 6 V to 9 V and back: the pulse follows.
        *(
            Beat(0.2, one_bulb, step=1, step_done=True, volts=v, finger_on=BULB_A)
            for v in (6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.0, 9.0, 8.0, 7.0, 6.0)
        ),
        # Step 2: a second bulb in series halves the current everywhere: 1.5 Hz.
        Beat(0.8, one_bulb, step=2),
        Beat(1.5, series, step=2, step_done=True, finger_on=BULB_A),
        Beat(1.5, series, step=2, step_done=True, finger_on=RIGHT_WIRE),
        # A hand hides a corner marker: the mat is lost and the pieces hold.
        Beat(0.7, series, step=2, step_done=True, mat_visible=False),
        # Step 3: in parallel each bulb gets 0.6 A (3 Hz) and the battery wire 1.2 A (6 Hz).
        Beat(0.8, one_bulb, step=3),
        Beat(1.5, parallel, step=3, step_done=True, finger_on=BRANCH),
        Beat(1.5, parallel, step=3, step_done=True, finger_on=BATTERY_WIRE),
        # Step 4: a wire across the bulb shorts the battery. The path buzzes; the bulb is dead.
        Beat(0.8, parallel, step=4),
        Beat(1.5, short, step=4, step_done=True, finger_on=BRANCH),
        Beat(1.0, short, step=4, step_done=True, finger_on=BULB_A),
        # After the lesson: a resistor in the loop, so the sample shows every piece type.
        Beat(2.0, with_resistor, step=4, step_done=True, lesson_done=True, finger_on=BOTTOM),
    ]


def states() -> Iterator[State]:
    """Every state message of the run, in order."""
    seq = 0
    for beat in beats():
        pieces, circuit = solve_pieces(beat.placed, beat.volts)
        step_id, prompt = STEPS[beat.step]
        lesson = LessonStep(
            lesson_id=LESSON_ID,
            step_id=step_id,
            step_index=beat.step,
            step_count=len(STEPS),
            prompt=prompt,
            step_done=beat.step_done,
            lesson_done=beat.lesson_done,
        )
        touch = _touch(beat, pieces)
        for _ in range(round(beat.seconds * FRAMES_PER_SECOND)):
            yield State(
                seq=seq,
                t=round(seq / FRAMES_PER_SECOND, 3),
                source="replay",
                mat_visible=beat.mat_visible,
                grid=GRID,
                pieces=pieces,
                circuit=circuit,
                touch=touch,
                lesson=lesson,
            )
            seq += 1


def _touch(beat: Beat, pieces: list) -> Touch:
    piece = next((p for p in pieces if p.id == beat.finger_on), None)
    if piece is None:
        return Touch()
    x = (piece.a[0] + piece.b[0]) / 2 / (GRID.cols - 1)
    y = (piece.a[1] + piece.b[1]) / 2 / (GRID.rows - 1)
    return touch_for(pieces, x=round(x, 3), y=round(y, 3), piece_id=piece.id)
