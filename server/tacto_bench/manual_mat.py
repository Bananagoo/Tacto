"""A mat you set by hand: the lab's source when there is no camera.

The UI team uses it to put the lab into any state on demand, and it is the
fallback if the camera misbehaves at the demo.
"""

from __future__ import annotations

import threading
from typing import Literal

from tacto.contract import Dot, Grid, PieceType, segment_id
from tacto.lab import MatView
from tacto.pieces import Placed
from tacto_mock.scenario import branch, loop

Tool = PieceType | Literal["erase"]

PRESETS: dict[str, list[Placed]] = {
    "empty": [],
    "open": loop(closed=False),
    "one_bulb": loop(closed=True),
    "series": loop(closed=True, bottom="bulb"),
    "parallel": loop(closed=True) + branch("bulb"),
    "short": loop(closed=True) + branch("wire"),
    "resistor": loop(closed=True, bottom="resistor"),
}


class ManualMat:
    """Pieces keyed by segment, changed by one tool at a time."""

    def __init__(self, grid: Grid) -> None:
        self.grid = grid
        self._lock = threading.Lock()
        self._pieces: dict[str, Placed] = {}
        self._finger: tuple[float, float] | None = None
        self._mat_visible = True

    def view(self) -> MatView:
        with self._lock:
            return MatView(tuple(self._pieces.values()), self._finger, self._mat_visible)

    def use_tool(self, tool: Tool, a: Dot, b: Dot) -> None:
        """Apply a tool to the segment between two dots.

        A piece tool on an empty segment, or on a different piece, places that piece.
        The same tool again acts on the piece: a switch toggles, a battery turns
        round, anything else comes off.
        """
        self._check_segment(a, b)
        key = segment_id(a, b)
        with self._lock:
            current = self._pieces.get(key)
            if tool == "erase":
                self._pieces.pop(key, None)
            elif current is None or current.type != tool:
                self._pieces[key] = Placed(tool, a, b)
            elif tool == "switch":
                self._pieces[key] = Placed("switch", current.a, current.b, not current.closed)
            elif tool == "battery":
                self._pieces[key] = Placed("battery", current.b, current.a)
            else:
                del self._pieces[key]

    def load_preset(self, name: str) -> None:
        pieces = PRESETS[name]
        with self._lock:
            self._pieces = {piece.id: piece for piece in pieces}

    def set_finger(self, position: tuple[float, float] | None) -> None:
        with self._lock:
            self._finger = position

    def set_mat_visible(self, visible: bool) -> None:
        with self._lock:
            self._mat_visible = visible

    def _check_segment(self, a: Dot, b: Dot) -> None:
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            raise ValueError(f"{a} and {b} are not neighbouring dots")
        for col, row in (a, b):
            if not (0 <= col < self.grid.cols and 0 <= row < self.grid.rows):
                raise ValueError(
                    f"dot {(col, row)} is off the {self.grid.cols}x{self.grid.rows} mat"
                )
