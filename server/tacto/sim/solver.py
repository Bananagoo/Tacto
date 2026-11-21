"""Parts and wires on the mat in, a fully solved `Circuit` out.

The graph step decides whether there is anything to solve. Only a closed circuit with
a non-zero source goes to ngspice; every other case is filled in with zeros here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from tacto.contract import Circuit, Dot, Part, Topology, Wire
from tacto.sim import engine
from tacto.sim.graph import (
    GraphAnalysis,
    analyse,
    is_resistive,
    is_zero_resistance,
    joins_two_dots,
)

# TODO(sim owner): measure the kit's real bulb and resistor and set these to match.
BULB_OHMS = 10.0
RESISTOR_OHMS = 10.0
# A bulb at this power is drawn fully lit: one 10 ohm bulb at 6 V.
FULL_BRIGHT_WATTS = 3.6
# Wires and closed switches get a tiny resistance so that each one has its own current
# and ngspice never sees a zero-ohm loop. Small enough to change currents by only ~0.02%.
WIRE_OHMS = 0.001
# How close two currents or voltages must be to count as "the same" when naming the
# topology, and the share of the battery's current below which a bulb counts as unlit.
RELATIVE_TOLERANCE = 0.01

DotVolts = Mapping[Dot, float]


def solve_circuit(parts: Sequence[Part], wires: Sequence[Wire], source_voltage: float) -> Circuit:
    """Solve the DC circuit on the mat. Inputs are not mutated; new models are returned.

    Currents are signed a -> b, and a part's voltage is the drop from its `a` to its `b`.
    Inside the battery current runs b -> a, so a battery that is supplying current reads
    negative.
    """
    analysis = analyse(parts, wires)
    volts = _dot_volts(parts, wires, analysis, source_voltage)
    solved_wires = [
        w.model_copy(
            update={
                "current": _current_amps(w, volts),
                "overloaded": index in analysis.overloaded_wires,
            }
        )
        for index, w in enumerate(wires)
    ]
    battery_amps = _battery_current_amps(analysis.battery, parts, wires, volts)
    solved_parts = [
        _solve_battery(p, analysis, source_voltage, battery_amps)
        if p is analysis.battery
        else _solve_part(p, volts)
        for p in parts
    ]
    total_current = abs(battery_amps)
    return Circuit(
        status=analysis.status,
        topology=_topology(solved_parts, total_current, source_voltage),
        source_voltage=source_voltage,
        total_current=total_current,
        parts=solved_parts,
        wires=solved_wires,
    )


def _dot_volts(
    parts: Sequence[Part], wires: Sequence[Wire], analysis: GraphAnalysis, source_voltage: float
) -> DotVolts:
    """Voltage at every dot that carries one. Empty when no current can flow."""
    if analysis.status != "closed" or analysis.battery is None or source_voltage == 0:
        return {}
    battery = analysis.battery
    # The battery's negative terminal is the reference. Dots off the battery's piece of
    # the graph are left out: ngspice cannot solve nodes that float.
    names = {dot: f"n{dot[0]}_{dot[1]}" for dot in analysis.live_dots}
    names[battery.b] = engine.GROUND
    resistors = [
        engine.Resistor(names[element.a], names[element.b], ohms)
        for element in (*parts, *wires)
        if element.a in names and (ohms := _resistance_ohms(element)) is not None
    ]
    node_volts = engine.solve_node_voltages(source_voltage, names[battery.a], resistors)
    return {dot: node_volts[name] for dot, name in names.items()}


def _resistance_ohms(element: Part | Wire) -> float | None:
    """Resistance of a conducting element, or None if no current can pass through it."""
    if isinstance(element, Wire):
        return WIRE_OHMS if joins_two_dots(element) else None
    if is_zero_resistance(element):
        return WIRE_OHMS
    if is_resistive(element):
        return BULB_OHMS if element.kind == "bulb" else RESISTOR_OHMS
    return None


def _drop_volts(element: Part | Wire, volts: DotVolts) -> float:
    """Voltage drop from `a` to `b`, or 0 for an element that is not part of the solved circuit."""
    if element.a not in volts or element.b not in volts or _resistance_ohms(element) is None:
        return 0.0
    return volts[element.a] - volts[element.b]


def _current_amps(element: Part | Wire, volts: DotVolts) -> float:
    ohms = _resistance_ohms(element)
    return 0.0 if ohms is None else _drop_volts(element, volts) / ohms


def _battery_current_amps(
    battery: Part | None, parts: Sequence[Part], wires: Sequence[Wire], volts: DotVolts
) -> float:
    """Current through the battery from `a` to `b`: minus what leaves `a` into the circuit."""
    if battery is None:
        return 0.0
    leaving_positive_terminal = [
        _current_amps(element, volts) * (1 if element.a == battery.a else -1)
        for element in (*parts, *wires)
        if battery.a in (element.a, element.b)
    ]
    # fsum is exact, so the total does not depend on the order of parts and wires.
    return -math.fsum(leaving_positive_terminal)


def _solve_battery(
    battery: Part, analysis: GraphAnalysis, source_voltage: float, battery_amps: float
) -> Part:
    # A shorted battery is shown with everything at zero: nothing is solved.
    voltage = 0.0 if analysis.status == "short" else source_voltage
    return battery.model_copy(update={"current": battery_amps, "voltage": voltage})


def _solve_part(part: Part, volts: DotVolts) -> Part:
    drop_volts = _drop_volts(part, volts)
    current_amps = _current_amps(part, volts)
    brightness = 0.0
    if part.kind == "bulb":
        # Brightness follows power, not current: half the current is a quarter as bright.
        brightness = min(1.0, drop_volts * current_amps / FULL_BRIGHT_WATTS)
    return part.model_copy(
        update={"current": current_amps, "voltage": drop_volts, "brightness": brightness}
    )


def _topology(parts: Sequence[Part], total_current: float, source_voltage: float) -> Topology:
    """How the lit bulbs are arranged, judged from the solved currents and voltages."""
    # A bulb bypassed by a wire still carries a sliver of current; it is not lit.
    lit_bulbs = [
        p for p in parts if p.kind == "bulb" and abs(p.current) > RELATIVE_TOLERANCE * total_current
    ]
    if not lit_bulbs:
        return "none"
    if len(lit_bulbs) == 1:
        return "single"
    if all(_same(abs(p.current), total_current) for p in lit_bulbs):
        return "series"
    if all(_same(abs(p.voltage), abs(source_voltage)) for p in lit_bulbs):
        return "parallel"
    return "mixed"


def _same(value: float, reference: float) -> bool:
    return math.isclose(value, reference, rel_tol=RELATIVE_TOLERANCE)
