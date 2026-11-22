"""What the mouse does for the current under the fingertip.

Vibration is current (amps): the tick rate and how hard each tick lands are both
proportional to the current through the part or wire being touched. It never encodes
voltage. Two things change together so that one bulb, two in series and two in parallel
are easy to tell apart in the hand: the rate alone only runs from 1.5 to 6 ticks a second.
"""

from __future__ import annotations

from tacto.sim.types import Circuit, Dot, Part, Probe, Wire

# TODO(sim owner): tune both on the real mouse.
# Ticks per second for each amp. Strictly proportional, with no offset, so that half the
# current feels like exactly half the rate. The web side caps the rate; do not cap it here.
HZ_PER_AMP = 5.0
# Below this the mouse stays silent, so solver rounding noise is never felt.
MIN_CURRENT_AMPS = 0.005
# TODO(Katie): tune on the real mouse. The current that gets full strength: two 10 ohm
# bulbs in parallel at the default 6 V draw 1.2 A at the battery, the most the lesson
# reaches without turning the voltage up. Strictly proportional below it, like the rate.
FULL_STRENGTH_AMPS = 1.2


def pulse_hz(current_amps: float) -> float:
    """Tick rate for a current. Direction does not matter; no current means silence."""
    if abs(current_amps) < MIN_CURRENT_AMPS:
        return 0.0
    return HZ_PER_AMP * abs(current_amps)


def strength(current_amps: float) -> float:
    """How hard the mouse should vibrate for a current, 0 to 1. Direction does not matter."""
    if abs(current_amps) < MIN_CURRENT_AMPS:
        return 0.0
    return min(1.0, abs(current_amps) / FULL_STRENGTH_AMPS)


def wire_id(a: Dot, b: Dot) -> str:
    """How a probe names the wire between two dots: "wire:c,r-c,r"."""
    return f"wire:{a[0]},{a[1]}-{b[0]},{b[1]}"


def probe_for(circuit: Circuit, *, present: bool, x: float, y: float, on: str | None) -> Probe:
    """The probe for a fingertip at (x, y) touching `on`: a part id or a wire id.

    A fingertip that is absent, or on nothing the circuit knows, gives a silent probe.
    """
    element = _find(circuit, on) if present and on is not None else None
    if element is None:
        return Probe(present=present, x=x, y=y)
    if isinstance(element, Wire) and element.overloaded:
        # A short is a warning, not a current reading: one continuous buzz, no ticks.
        return Probe(present=present, x=x, y=y, on=on, buzz=True)
    return Probe(
        present=present,
        x=x,
        y=y,
        on=on,
        current=element.current,
        pulse_hz=pulse_hz(element.current),
    )


def _find(circuit: Circuit, on: str) -> Part | Wire | None:
    for part in circuit.parts:
        if part.id == on:
            return part
    for wire in circuit.wires:
        # Vision may name a wire from either end.
        if on in (wire_id(wire.a, wire.b), wire_id(wire.b, wire.a)):
            return wire
    return None
