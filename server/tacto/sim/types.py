"""The solver's own data: parts and wires between any two dots, and the solved circuit.

The lab speaks in pieces on segments (`tacto.contract`); `tacto.pieces` translates.
These types stay inside `sim/` so the solver can be tested, and changed, on its own.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Dot = tuple[int, int]

PartKind = Literal["battery", "bulb", "resistor", "switch"]
CircuitStatus = Literal["empty", "open", "closed", "short"]
# How the lit bulbs are arranged. "mixed" is anything that is neither pure series nor parallel.
Topology = Literal["none", "single", "series", "parallel", "mixed"]


class Part(BaseModel):
    id: str
    kind: PartKind
    a: Dot  # for a battery, the positive terminal
    b: Dot
    closed: bool | None = None  # switches only
    current: float = 0.0  # amps, signed a -> b
    voltage: float = 0.0  # volts across the part
    brightness: float = Field(0.0, ge=0.0, le=1.0)  # bulbs only


class Wire(BaseModel):
    a: Dot
    b: Dot
    current: float = 0.0  # amps, signed a -> b
    overloaded: bool = False  # on the path of a short circuit


class Circuit(BaseModel):
    status: CircuitStatus = "empty"
    topology: Topology = "none"
    source_voltage: float = 0.0
    total_current: float = 0.0
    parts: list[Part] = []
    wires: list[Wire] = []


class Probe(BaseModel):
    """What the mouse should do for a fingertip on one part or wire."""

    present: bool = False
    x: float = 0.0
    y: float = 0.0
    on: str | None = None  # part id, or "wire:c,r-c,r", or None
    current: float = 0.0
    pulse_hz: float = 0.0  # tick rate for the mouse; 0 means silent
    buzz: bool = False  # on a shorted path: one hard continuous buzz, not ticks
