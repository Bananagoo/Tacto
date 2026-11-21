"""Schematic symbols, drawn between two points on a page so each fills the gap it sits in."""

from __future__ import annotations

import math
from typing import Literal

from .page_canvas import PageCanvas, PointMm, SegmentFrame

Symbol = Literal["wire", "battery", "bulb", "resistor", "switch"]

WIRE_WIDTH_MM = 2.0
_STROKE_MM = 1.0  # the lines of a symbol's body, thinner than the wire so it reads as a part
_MIN_LEAD_MM = 2.0  # wire kept at each end, however short the gap

_BULB_RADIUS_MM = 6.0
_BATTERY_PLATE_GAP_MM = 3.0
_BATTERY_POSITIVE_HALF_MM = 6.5  # the positive plate is the long thin one
_BATTERY_NEGATIVE_HALF_MM = 3.5
_BATTERY_NEGATIVE_WIDTH_MM = 2.4
_PLUS_HEIGHT_MM = 3.0
_RESISTOR_HALF_LENGTH_MM = 8.0
_RESISTOR_AMPLITUDE_MM = 3.0
_RESISTOR_ZIGS = 6
_SWITCH_HALF_LENGTH_MM = 5.0
_SWITCH_CONTACT_RADIUS_MM = 1.6


def _body_half_mm(frame: SegmentFrame, wanted_mm: float) -> float:
    """Half the symbol's length, shrunk if the gap is too short to leave leads."""
    return min(wanted_mm, frame.length_mm / 2 - _MIN_LEAD_MM)


def draw_symbol(canvas: PageCanvas, symbol: Symbol, a: PointMm, b: PointMm) -> None:
    """Draw a part from a to b, wired to both ends. A battery's positive plate faces a."""
    if symbol == "wire" or math.dist(a, b) <= 2 * _MIN_LEAD_MM:
        canvas.line(a, b, width_mm=WIRE_WIDTH_MM)
        return
    frame = SegmentFrame(a, b)
    half_mm = _BODIES[symbol](canvas, frame)
    canvas.line(a, frame.at(-half_mm), width_mm=WIRE_WIDTH_MM)
    canvas.line(frame.at(half_mm), b, width_mm=WIRE_WIDTH_MM)


def _bulb(canvas: PageCanvas, frame: SegmentFrame) -> float:
    radius_mm = _body_half_mm(frame, _BULB_RADIUS_MM)
    canvas.circle(frame.at(0), radius_mm, width_mm=_STROKE_MM)
    reach_mm = radius_mm / math.sqrt(2)
    canvas.line(frame.at(-reach_mm, -reach_mm), frame.at(reach_mm, reach_mm), width_mm=_STROKE_MM)
    canvas.line(frame.at(-reach_mm, reach_mm), frame.at(reach_mm, -reach_mm), width_mm=_STROKE_MM)
    return radius_mm


def _battery(canvas: PageCanvas, frame: SegmentFrame) -> float:
    half_mm = _body_half_mm(frame, _BATTERY_PLATE_GAP_MM / 2)
    canvas.line(
        frame.at(-half_mm, -_BATTERY_POSITIVE_HALF_MM),
        frame.at(-half_mm, _BATTERY_POSITIVE_HALF_MM),
        width_mm=_STROKE_MM,
    )
    canvas.line(
        frame.at(half_mm, -_BATTERY_NEGATIVE_HALF_MM),
        frame.at(half_mm, _BATTERY_NEGATIVE_HALF_MM),
        width_mm=_BATTERY_NEGATIVE_WIDTH_MM,
    )
    canvas.text("+", frame.at(-half_mm - 4.0, _BATTERY_POSITIVE_HALF_MM), height_mm=_PLUS_HEIGHT_MM)
    return half_mm


def _resistor(canvas: PageCanvas, frame: SegmentFrame) -> float:
    half_mm = _body_half_mm(frame, _RESISTOR_HALF_LENGTH_MM)
    step_mm = 2 * half_mm / _RESISTOR_ZIGS
    points = [frame.at(-half_mm)]
    for zig in range(_RESISTOR_ZIGS):
        side = -1 if zig % 2 == 0 else 1
        points.append(frame.at(-half_mm + (zig + 0.5) * step_mm, side * _RESISTOR_AMPLITUDE_MM))
    points.append(frame.at(half_mm))
    canvas.polyline(points, width_mm=_STROKE_MM)
    return half_mm


def _switch(canvas: PageCanvas, frame: SegmentFrame) -> float:
    """A closed switch: a tile in a slot always conducts, and an open switch is no tile."""
    half_mm = _body_half_mm(frame, _SWITCH_HALF_LENGTH_MM)
    canvas.line(frame.at(-half_mm), frame.at(half_mm), width_mm=_STROKE_MM)
    for end_mm in (-half_mm, half_mm):
        canvas.circle(frame.at(end_mm), _SWITCH_CONTACT_RADIUS_MM)
    return half_mm


_BODIES = {"bulb": _bulb, "battery": _battery, "resistor": _resistor, "switch": _switch}
