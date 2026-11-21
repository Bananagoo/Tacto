"""Pieces on the mat in, solved pieces and the circuit summary out.

This is the bridge from the segment model (one piece between two neighbouring dots)
to the solver in `sim/`. Wires and closed switches both go to the solver as plain
wires, because electrically they are the same thing; an open switch is a gap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from tacto.contract import Circuit, CircuitStatus, Dot, Piece, PieceType, Touch, segment_id
from tacto.sim.feel import pulse_hz, strength
from tacto.sim.solver import solve_circuit
from tacto.sim.types import Part, Wire

_STATUS: dict[str, CircuitStatus] = {
    "empty": "open",
    "open": "open",
    "closed": "working",
    "short": "shorted",
}


@dataclass(frozen=True)
class Placed:
    """A piece as the mat reader (or a person at the bench) reports it: no physics yet."""

    type: PieceType
    a: Dot  # for a battery, the positive end
    b: Dot
    closed: bool = False  # switches only

    @property
    def id(self) -> str:
        return segment_id(self.a, self.b)

    @property
    def conducts_freely(self) -> bool:
        return self.type == "wire" or (self.type == "switch" and self.closed)


def solve_pieces(placed: Sequence[Placed], volts: float) -> tuple[list[Piece], Circuit]:
    """Solve the circuit the placed pieces make, at the given battery voltage."""
    free = [p for p in placed if p.conducts_freely]
    parts = [
        Part(id=p.id, kind=p.type, a=p.a, b=p.b)  # type: ignore[arg-type]
        for p in placed
        if p.type in ("battery", "bulb", "resistor")
    ]
    solved = solve_circuit(parts, [Wire(a=p.a, b=p.b) for p in free], volts)
    status = _STATUS[solved.status]
    part_by_id = {part.id: part for part in solved.parts}
    wire_by_id = {p.id: wire for p, wire in zip(free, solved.wires, strict=True)}
    battery_id = next((p.id for p in solved.parts if p.kind == "battery"), None)

    pieces: list[Piece] = []
    for p in placed:
        part, wire = part_by_id.get(p.id), wire_by_id.get(p.id)
        pieces.append(
            Piece(
                id=p.id,
                type=p.type,
                a=p.a,
                b=p.b,
                closed=p.closed if p.type == "switch" else None,
                current=_tidy(part.current if part else wire.current if wire else 0.0),
                brightness=_tidy(part.brightness) if part and p.type == "bulb" else None,
                shorted=(wire is not None and wire.overloaded)
                or (status == "shorted" and p.id == battery_id),
            )
        )
    circuit = Circuit(
        status=status,
        voltage=volts,
        total_current=_tidy(solved.total_current),
        shorted_path=_walk_loop([piece for piece in pieces if piece.shorted]),
    )
    return pieces, circuit


def touch_for(pieces: Sequence[Piece], *, x: float, y: float, piece_id: str | None) -> Touch:
    """What the mouse should play for a fingertip at (x, y) over `piece_id`."""
    piece = next((p for p in pieces if p.id == piece_id), None)
    if piece is None:
        return Touch(present=True, x=x, y=y)
    if piece.shorted:
        # A short is a warning, not a current reading: one continuous buzz, no ticks.
        return Touch(present=True, x=x, y=y, piece_id=piece.id, buzz=True, strength=1.0)
    return Touch(
        present=True,
        x=x,
        y=y,
        piece_id=piece.id,
        pulse_hz=round(pulse_hz(piece.current), 2),
        strength=round(strength(piece.current), 3),
    )


def _tidy(value: float) -> float:
    # The solver gives wires a tiny resistance, so 0.6 A arrives as 0.59988. Four
    # places is finer than anything the screen or the mouse can show.
    return round(value, 4) + 0.0


def _walk_loop(shorted: Sequence[Piece]) -> list[str]:
    """Piece ids in order round the shorted loop, starting at the battery.

    When the shorted pieces do not form one simple loop (two shorting paths at once),
    the ones the walk could not reach follow in mat order.
    """
    battery = next((p for p in shorted if p.type == "battery"), None)
    if battery is None:
        return [p.id for p in shorted]
    order, dot = [battery.id], battery.a
    remaining = {p.id: p for p in shorted if p.id != battery.id}
    while remaining:
        step = next((p for p in remaining.values() if dot in (p.a, p.b)), None)
        if step is None:
            break
        order.append(step.id)
        dot = step.b if step.a == dot else step.a
        del remaining[step.id]
    return order + sorted(remaining)


def warm_up_solver() -> None:
    """Load ngspice now. Its first solve takes about 0.4 s; every later one about 1 ms.

    Call once at startup so the learner's first closed loop is not the slow one.
    """
    solve_pieces([Placed("battery", (0, 0), (0, 1)), Placed("bulb", (0, 0), (1, 0))], 1.0)
    solve_pieces(
        [
            Placed("battery", (0, 0), (0, 1)),
            Placed("bulb", (0, 0), (1, 0)),
            Placed("wire", (1, 0), (1, 1)),
            Placed("wire", (1, 1), (0, 1)),
        ],
        1.0,
    )
