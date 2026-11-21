"""Which part or wire is a fingertip on?"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..contract import Dot, Part, Wire

# How far from a wire or part, in dot spacings, a fingertip still counts as on it.
# TODO(vision owner): tune on the real mat; hand tracking jitters by a few millimetres.
REACH_DOTS = 0.35


def element_at(
    parts: Sequence[Part],
    wires: Sequence[Wire],
    *,
    cols: int,
    rows: int,
    x: float,
    y: float,
) -> Part | Wire | None:
    """The nearest part or wire within reach of mat position (x, y), or None.

    x and y run 0..1 from the first dot column or row to the last. A part wins a tie with
    a wire, so a fingertip on a bulb reads as the bulb and not the wire entering it.
    """
    point = (x * (cols - 1), y * (rows - 1))
    best: Part | Wire | None = None
    best_distance = REACH_DOTS
    for element in (*parts, *wires):
        distance = _distance_to_segment(point, element.a, element.b)
        if distance < best_distance:
            best, best_distance = element, distance
    return best


def _distance_to_segment(point: tuple[float, float], a: Dot, b: Dot) -> float:
    px, py = point
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.hypot(px - a[0], py - a[1])
    # How far along the segment the closest point is, held between its two ends.
    along = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / length_squared))
    return math.hypot(px - (a[0] + along * dx), py - (a[1] + along * dy))
