"""Solver: parts and wires in, a fully solved Circuit out.

All circuits run at 6 V with 10 ohm bulbs. Wires are modelled as 1 milliohm, so the
hand-worked answers below hold to well within the tolerances used here.
"""

import random
import time

import pytest

from tacto.sim import engine, solve_circuit
from tacto.sim.types import Circuit, Dot, Part, Wire

from .conftest import (
    SOURCE_VOLTS,
    battery,
    bulb,
    one_bulb,
    part,
    two_in_parallel,
    two_in_series,
    wire,
)

AMPS = 1e-3  # tolerance: wire resistance shifts currents by about 0.02%
VOLTS = 1e-2
NO_AMPS = 1e-9  # "no current" for elements ngspice did solve: floating-point noise only
BRIGHTNESS = 1e-2


def by_id(circuit: Circuit) -> dict[str, Part]:
    return {p.id: p for p in circuit.parts}


def current_into(circuit: Circuit, dot: Dot) -> float:
    """Net current arriving at `dot` through every part and wire that touches it."""
    total = 0.0
    for element in [*circuit.parts, *circuit.wires]:
        if element.b == dot:
            total += element.current
        if element.a == dot:
            total -= element.current
    return total


def forbid_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("ngspice must not be called for this circuit")

    monkeypatch.setattr(engine, "solve_node_voltages", fail)


def test_one_bulb():
    """I = V / R = 6 / 10 = 0.6 A round the whole loop. The bulb drops all 6 V.

    Power = 6 * 0.6 = 3.6 W = full brightness. Current leaves the battery's + at (0,1),
    so it runs a -> b in both wires and in the bulb, and b -> a inside the battery.
    """
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    assert circuit.status == "closed"
    assert circuit.topology == "single"
    assert circuit.source_voltage == SOURCE_VOLTS
    assert circuit.total_current == pytest.approx(0.6, abs=AMPS)
    assert [w.current for w in circuit.wires] == pytest.approx([0.6, 0.6], abs=AMPS)
    parts = by_id(circuit)
    assert parts["A"].current == pytest.approx(0.6, abs=AMPS)
    assert parts["A"].voltage == pytest.approx(6.0, abs=VOLTS)
    assert parts["A"].brightness == pytest.approx(1.0, abs=BRIGHTNESS)
    assert parts["bat"].current == pytest.approx(-0.6, abs=AMPS)
    assert parts["bat"].voltage == SOURCE_VOLTS
    assert parts["bat"].brightness == 0.0


def test_two_bulbs_in_series():
    """R = 10 + 10 = 20 ohms, so I = 6 / 20 = 0.3 A everywhere and each bulb drops 3 V.

    Power per bulb = 3 * 0.3 = 0.9 W; 0.9 / 3.6 = 0.25: clearly dim, not half.
    """
    circuit = solve_circuit(*two_in_series(), SOURCE_VOLTS)
    assert circuit.status == "closed"
    assert circuit.topology == "series"
    assert circuit.total_current == pytest.approx(0.3, abs=AMPS)
    assert [w.current for w in circuit.wires] == pytest.approx([0.3, 0.3], abs=AMPS)
    for bulb_id in ("A", "B"):
        solved = by_id(circuit)[bulb_id]
        assert solved.current == pytest.approx(0.3, abs=AMPS)
        assert solved.voltage == pytest.approx(3.0, abs=VOLTS)
        assert solved.brightness == pytest.approx(0.25, abs=BRIGHTNESS)


def test_two_bulbs_in_parallel():
    """Each bulb has the full 6 V, so each carries 6 / 10 = 0.6 A at full brightness.

    The battery supplies both: 0.6 + 0.6 = 1.2 A through it and through the two wires
    that connect it to the junctions. The wires of bulb B's branch carry B's 0.6 A.
    """
    circuit = solve_circuit(*two_in_parallel(), SOURCE_VOLTS)
    assert circuit.status == "closed"
    assert circuit.topology == "parallel"
    assert circuit.total_current == pytest.approx(1.2, abs=AMPS)
    battery_top, battery_bottom, branch_out, branch_back = circuit.wires
    assert battery_top.current == pytest.approx(1.2, abs=AMPS)
    assert battery_bottom.current == pytest.approx(1.2, abs=AMPS)
    assert branch_out.current == pytest.approx(0.6, abs=AMPS)
    assert branch_back.current == pytest.approx(0.6, abs=AMPS)
    for bulb_id in ("A", "B"):
        solved = by_id(circuit)[bulb_id]
        assert solved.current == pytest.approx(0.6, abs=AMPS)
        assert solved.voltage == pytest.approx(6.0, abs=VOLTS)
        assert solved.brightness == pytest.approx(1.0, abs=BRIGHTNESS)


def test_kirchhoff_current_law_at_every_dot():
    """Parallel circuit: at junction (4,1), 1.2 A arrives and 0.6 + 0.6 A leaves: net 0.

    The same must hold at every dot, the battery's terminals included.
    """
    circuit = solve_circuit(*two_in_parallel(), SOURCE_VOLTS)
    dots = {dot for element in [*circuit.parts, *circuit.wires] for dot in (element.a, element.b)}
    assert (4, 1) in dots
    for dot in dots:
        assert current_into(circuit, dot) == pytest.approx(0.0, abs=NO_AMPS)


def test_reversing_a_wire_flips_the_sign_of_its_current():
    """The top wire carries 0.6 A away from the battery's +. Drawn (4,1) -> (0,1), that
    same flow is b -> a, so it reads -0.6 A. Nothing else changes."""
    parts, wires = one_bulb()
    wires[0] = wire((4, 1), (0, 1))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.wires[0].current == pytest.approx(-0.6, abs=AMPS)
    assert circuit.wires[1].current == pytest.approx(0.6, abs=AMPS)
    assert by_id(circuit)["A"].current == pytest.approx(0.6, abs=AMPS)


def test_reversing_a_bulb_flips_its_current_and_voltage_but_not_its_brightness():
    """Bulb placed b-side up: 0.6 A flows b -> a, so current is -0.6 A and the a -> b drop
    is -6 V. Power is still 6 * 0.6 = 3.6 W: full brightness."""
    parts, wires = one_bulb()
    parts[1] = bulb("A", (4, 3), (4, 1))
    solved = by_id(solve_circuit(parts, wires, SOURCE_VOLTS))["A"]
    assert solved.current == pytest.approx(-0.6, abs=AMPS)
    assert solved.voltage == pytest.approx(-6.0, abs=VOLTS)
    assert solved.brightness == pytest.approx(1.0, abs=BRIGHTNESS)


def test_bulb_on_a_dead_end_stub_is_dark_and_the_loop_still_runs():
    """Bulb S hangs off (4,3) and its far end joins nothing: no path, so 0 A.

    The loop itself is unchanged: 6 / 10 = 0.6 A, and S does not count as lit.
    """
    parts, wires = one_bulb()
    parts.append(bulb("S", (4, 3), (4, 5)))
    wires.append(wire((4, 5), (6, 5)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.status == "closed"
    assert circuit.topology == "single"
    assert circuit.total_current == pytest.approx(0.6, abs=AMPS)
    stub = by_id(circuit)["S"]
    # ngspice leaves rounding noise of about 1e-17 on the stub; anything that small is zero.
    assert stub.current == pytest.approx(0.0, abs=NO_AMPS)
    assert stub.voltage == pytest.approx(0.0, abs=NO_AMPS)
    assert stub.brightness == pytest.approx(0.0, abs=NO_AMPS)
    assert circuit.wires[2].current == pytest.approx(0.0, abs=NO_AMPS)


def test_island_not_connected_to_the_battery_never_reaches_ngspice():
    """A bulb and wire loop drawn elsewhere on the mat would be floating nodes for
    ngspice. It is left out and keeps zero current; the real loop still gives 0.6 A."""
    parts, wires = one_bulb()
    parts.append(bulb("I", (8, 6), (8, 8)))
    wires.append(wire((8, 6), (8, 8)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.total_current == pytest.approx(0.6, abs=AMPS)
    assert by_id(circuit)["I"].current == 0.0
    assert circuit.wires[2].current == 0.0


def test_series_resistor_and_closed_switch():
    """Bulb (10) + resistor (10) in series through a closed switch: 6 / 20 = 0.3 A.

    The resistor drops 0.3 * 10 = 3 V and never glows. The switch drops nothing.
    One lit bulb, so the topology is `single`.
    """
    parts = [
        battery(),
        part("sw", "switch", (0, 1), (2, 1), closed=True),
        part("R", "resistor", (2, 1), (4, 1)),
        bulb("A", (4, 1), (4, 3)),
    ]
    circuit = solve_circuit(parts, [wire((4, 3), (0, 3))], SOURCE_VOLTS)
    solved = by_id(circuit)
    assert circuit.topology == "single"
    assert circuit.total_current == pytest.approx(0.3, abs=AMPS)
    assert solved["R"].current == pytest.approx(0.3, abs=AMPS)
    assert solved["R"].voltage == pytest.approx(3.0, abs=VOLTS)
    assert solved["R"].brightness == 0.0
    assert solved["sw"].current == pytest.approx(0.3, abs=AMPS)
    assert solved["sw"].voltage == pytest.approx(0.0, abs=VOLTS)
    assert solved["A"].brightness == pytest.approx(0.25, abs=BRIGHTNESS)


def test_series_bulb_feeding_a_parallel_pair_is_mixed():
    """Bulb S in series with bulbs A and B in parallel: R = 10 + (10 || 10) = 15 ohms.

    I = 6 / 15 = 0.4 A through S (4 V across it); A and B share it, 0.2 A each at 2 V.
    A and B carry neither the full current nor the full voltage: `mixed`.
    """
    parts, wires = two_in_parallel()
    wires[0] = wire((2, 1), (4, 1))
    parts.append(bulb("S", (0, 1), (2, 1)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    solved = by_id(circuit)
    assert circuit.topology == "mixed"
    assert circuit.total_current == pytest.approx(0.4, abs=AMPS)
    assert solved["S"].voltage == pytest.approx(4.0, abs=VOLTS)
    assert solved["A"].current == pytest.approx(0.2, abs=AMPS)
    assert solved["B"].current == pytest.approx(0.2, abs=AMPS)


def test_bulb_bypassed_by_a_wire_is_not_lit():
    """Two bulbs in series, with a wire drawn across bulb B. The wire takes B's current,
    so only A is lit: 6 / 10 = 0.6 A, topology `single`, B dark."""
    parts, wires = two_in_series()
    wires.append(wire((2, 1), (4, 1)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    solved = by_id(circuit)
    assert circuit.status == "closed"
    assert circuit.topology == "single"
    assert solved["A"].current == pytest.approx(0.6, abs=AMPS)
    assert solved["B"].current == pytest.approx(0.0, abs=AMPS)
    assert solved["B"].brightness == pytest.approx(0.0, abs=BRIGHTNESS)


def test_two_wires_on_the_same_dots_share_the_current():
    """A second top wire drawn over the first: the loop still carries 0.6 A in total,
    0.3 A in each of the twin wires, and 0.6 A (not 1.2) through the bulb."""
    parts, wires = one_bulb()
    wires.append(wire((4, 1), (0, 1)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.total_current == pytest.approx(0.6, abs=AMPS)
    assert circuit.wires[0].current == pytest.approx(0.3, abs=AMPS)
    assert circuit.wires[2].current == pytest.approx(-0.3, abs=AMPS)
    assert by_id(circuit)["A"].current == pytest.approx(0.6, abs=AMPS)


def test_two_bulbs_on_the_same_dots_are_in_parallel():
    """Bulb B placed on the same two dots as A: each has 6 V and carries 0.6 A; 1.2 A total."""
    parts, wires = one_bulb()
    parts.append(bulb("B", (4, 1), (4, 3)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.topology == "parallel"
    assert circuit.total_current == pytest.approx(1.2, abs=AMPS)
    assert by_id(circuit)["A"].current == pytest.approx(0.6, abs=AMPS)
    assert by_id(circuit)["B"].current == pytest.approx(0.6, abs=AMPS)


def test_wire_to_itself_and_part_on_one_dot_are_ignored():
    """Degenerate elements join nothing: the loop still gives 0.6 A and they carry 0 A."""
    parts, wires = one_bulb()
    parts.append(bulb("dot", (4, 1), (4, 1)))
    wires.append(wire((0, 1), (0, 1)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.topology == "single"
    assert circuit.total_current == pytest.approx(0.6, abs=AMPS)
    assert by_id(circuit)["dot"].current == 0.0
    assert circuit.wires[2].current == 0.0


def test_short_zeroes_everything_and_marks_the_hot_wires(monkeypatch: pytest.MonkeyPatch):
    """A wire straight across the battery of a lit loop. Nothing is solved: every current,
    voltage and brightness is 0, and only the shorting wire is overloaded."""
    forbid_engine(monkeypatch)
    parts, wires = one_bulb()
    wires.append(wire((0, 1), (0, 3)))
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert circuit.status == "short"
    assert circuit.topology == "none"
    assert circuit.total_current == 0.0
    assert circuit.source_voltage == SOURCE_VOLTS
    for solved in circuit.parts:
        assert (solved.current, solved.voltage, solved.brightness) == (0.0, 0.0, 0.0)
    assert [w.current for w in circuit.wires] == [0.0, 0.0, 0.0]
    assert [w.overloaded for w in circuit.wires] == [False, False, True]


def test_open_and_empty_never_reach_ngspice(monkeypatch: pytest.MonkeyPatch):
    """No loop means no current: status only, and the battery still shows its 6 V."""
    forbid_engine(monkeypatch)
    assert solve_circuit([], [], SOURCE_VOLTS).status == "empty"
    parts, wires = one_bulb()
    circuit = solve_circuit(parts, wires[:1], SOURCE_VOLTS)
    assert circuit.status == "open"
    assert circuit.topology == "none"
    assert circuit.total_current == 0.0
    assert by_id(circuit)["bat"].voltage == SOURCE_VOLTS
    assert by_id(circuit)["A"].current == 0.0


def test_zero_volts_is_closed_with_no_current(monkeypatch: pytest.MonkeyPatch):
    """Wheel turned right down: the loop is complete but 0 / 10 = 0 A flows."""
    forbid_engine(monkeypatch)
    circuit = solve_circuit(*one_bulb(), 0.0)
    assert circuit.status == "closed"
    assert circuit.topology == "none"
    assert circuit.total_current == 0.0
    assert by_id(circuit)["A"].current == 0.0


def test_stale_values_on_the_inputs_are_replaced():
    """A caller may pass last frame's solved models back in; an open loop must read 0 A."""
    parts, wires = one_bulb()
    parts[1] = parts[1].model_copy(update={"current": 0.6, "voltage": 6.0, "brightness": 1.0})
    wires[0] = Wire(a=(0, 1), b=(4, 1), current=0.6, overloaded=True)
    circuit = solve_circuit(parts, wires[:1], SOURCE_VOLTS)
    solved = by_id(circuit)["A"]
    assert (solved.current, solved.voltage, solved.brightness) == (0.0, 0.0, 0.0)
    assert (circuit.wires[0].current, circuit.wires[0].overloaded) == (0.0, False)


def test_inputs_are_not_mutated():
    parts, wires = two_in_parallel()
    parts_before = [p.model_copy(deep=True) for p in parts]
    wires_before = [w.model_copy(deep=True) for w in wires]
    circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
    assert parts == parts_before
    assert wires == wires_before
    assert all(solved is not given for solved, given in zip(circuit.parts, parts, strict=True))
    assert all(solved is not given for solved, given in zip(circuit.wires, wires, strict=True))


def test_result_does_not_depend_on_input_order():
    """The same mat read in a different order gives the same number for every element."""
    parts, wires = two_in_parallel()
    parts.append(bulb("S", (0, 1), (2, 1)))
    wires[0] = wire((2, 1), (4, 1))
    reference = solve_circuit(parts, wires, SOURCE_VOLTS)
    shuffler = random.Random(7)
    for _ in range(5):
        shuffled_parts, shuffled_wires = parts[:], wires[:]
        shuffler.shuffle(shuffled_parts)
        shuffler.shuffle(shuffled_wires)
        circuit = solve_circuit(shuffled_parts, shuffled_wires, SOURCE_VOLTS)
        assert by_id(circuit) == by_id(reference)
        assert {(w.a, w.b): w for w in circuit.wires} == {(w.a, w.b): w for w in reference.wires}
        assert (circuit.status, circuit.topology) == (reference.status, reference.topology)
        assert circuit.total_current == reference.total_current


def test_output_keeps_the_input_order():
    parts, wires = two_in_parallel()
    circuit = solve_circuit(parts[::-1], wires[::-1], SOURCE_VOLTS)
    assert [p.id for p in circuit.parts] == [p.id for p in parts[::-1]]
    assert [(w.a, w.b) for w in circuit.wires] == [(w.a, w.b) for w in wires[::-1]]


def test_repeated_solves_are_fast():
    """The loop solves every frame: after the first call (which loads ngspice) one solve
    must take under 5 ms. Best of several, so a busy machine does not fail the test."""
    parts, wires = two_in_parallel()
    solve_circuit(parts, wires, SOURCE_VOLTS)
    durations_ms = []
    for step in range(20):
        start = time.perf_counter()
        solve_circuit(parts, wires, SOURCE_VOLTS + 0.1 * step)
        durations_ms.append((time.perf_counter() - start) * 1000)
    assert min(durations_ms) < 5.0
