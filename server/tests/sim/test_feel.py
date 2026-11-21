"""Feel: current under the fingertip -> what the mouse does. Vibration is current (amps)."""

import pytest

from tacto.sim import probe_for, solve_circuit
from tacto.sim.feel import pulse_hz
from tacto.sim.types import Circuit

from .conftest import SOURCE_VOLTS, one_bulb, two_in_parallel, two_in_series, wire


def shorted_loop() -> Circuit:
    """One-bulb loop with a wire [index 2] drawn straight across the battery."""
    parts, wires = one_bulb()
    return solve_circuit(parts, [*wires, wire((0, 1), (0, 3))], SOURCE_VOLTS)


def test_no_current_is_silent():
    assert pulse_hz(0.0) == 0.0


def test_tiny_current_is_silent():
    """Below 5 mA the mouse stays still: 0.004 A -> 0 Hz, in either direction."""
    assert pulse_hz(0.004) == 0.0
    assert pulse_hz(-0.004) == 0.0


def test_rate_is_proportional_to_current():
    """5 Hz per amp with no offset: 0.3 A -> 1.5 Hz, 0.6 A -> 3.0 Hz, 1.2 A -> 6.0 Hz.

    Doubling the current exactly doubles the rate; the lesson depends on it.
    """
    assert pulse_hz(0.3) == pytest.approx(1.5)
    assert pulse_hz(0.6) == pytest.approx(3.0)
    assert pulse_hz(1.2) == pytest.approx(6.0)
    assert pulse_hz(0.6) == 2 * pulse_hz(0.3)


def test_rate_is_not_capped_here():
    """The web side owns the cap: 4 A -> 20 Hz comes straight through."""
    assert pulse_hz(4.0) == pytest.approx(20.0)


def test_direction_does_not_change_the_rate():
    assert pulse_hz(-0.6) == pulse_hz(0.6)


def test_the_three_lesson_circuits_feel_different():
    """One bulb 0.6 A -> 3 Hz; two in series 0.3 A -> 1.5 Hz; the parallel circuit's
    battery wire 1.2 A -> 6 Hz. Same fingertip position, on the top wire, each time."""
    rates = []
    for layout in (one_bulb, two_in_series, two_in_parallel):
        parts, wires = layout()
        circuit = solve_circuit(parts, wires, SOURCE_VOLTS)
        top = circuit.wires[0]
        on = f"wire:{top.a[0]},{top.a[1]}-{top.b[0]},{top.b[1]}"
        rates.append(probe_for(circuit, present=True, x=0.2, y=0.1, on=on).pulse_hz)
    assert rates == pytest.approx([3.0, 1.5, 6.0], abs=0.01)


def test_probe_on_a_part():
    """Fingertip on bulb A of the one-bulb loop: 0.6 A, so 5 * 0.6 = 3 Hz."""
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    probe = probe_for(circuit, present=True, x=0.4, y=0.5, on="A")
    assert (probe.present, probe.x, probe.y, probe.on) == (True, 0.4, 0.5, "A")
    assert probe.current == pytest.approx(0.6, abs=1e-3)
    assert probe.pulse_hz == pytest.approx(3.0, abs=0.01)
    assert probe.buzz is False


def test_probe_on_the_battery_keeps_the_signed_current():
    """Inside the battery current runs b -> a: -0.6 A, but the rate is still 3 Hz."""
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    probe = probe_for(circuit, present=True, x=0.0, y=0.5, on="bat")
    assert probe.current == pytest.approx(-0.6, abs=1e-3)
    assert probe.pulse_hz == pytest.approx(3.0, abs=0.01)


def test_probe_on_a_wire_in_either_direction():
    """The top wire is drawn (0,1) -> (4,1) and carries 0.6 A. Naming it from either end
    finds the same wire and reports that wire's own signed current."""
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    for on in ("wire:0,1-4,1", "wire:4,1-0,1"):
        probe = probe_for(circuit, present=True, x=0.2, y=0.1, on=on)
        assert probe.on == on
        assert probe.current == pytest.approx(0.6, abs=1e-3)
        assert probe.pulse_hz == pytest.approx(3.0, abs=0.01)


def test_probe_on_twin_wires_reports_one_wire_not_the_sum():
    """Two wires on the same dots carry 0.3 A each; the probe feels one of them: 1.5 Hz."""
    parts, wires = one_bulb()
    circuit = solve_circuit(parts, [*wires, wire((0, 1), (4, 1))], SOURCE_VOLTS)
    probe = probe_for(circuit, present=True, x=0.2, y=0.1, on="wire:0,1-4,1")
    assert probe.current == pytest.approx(0.3, abs=1e-3)
    assert probe.pulse_hz == pytest.approx(1.5, abs=0.01)


@pytest.mark.parametrize("on", [None, "nope", "wire:9,9-8,8", "wire:garbage", "wire:"])
def test_probe_on_nothing_known_is_silent(on: str | None):
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    probe = probe_for(circuit, present=True, x=0.7, y=0.2, on=on)
    assert (probe.present, probe.x, probe.y) == (True, 0.7, 0.2)
    assert (probe.on, probe.current, probe.pulse_hz, probe.buzz) == (None, 0.0, 0.0, False)


def test_probe_not_present_is_silent_even_over_a_live_part():
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    probe = probe_for(circuit, present=False, x=0.4, y=0.5, on="A")
    assert (probe.present, probe.x, probe.y) == (False, 0.4, 0.5)
    assert (probe.on, probe.current, probe.pulse_hz, probe.buzz) == (None, 0.0, 0.0, False)


def test_probe_on_an_overloaded_wire_buzzes():
    """The shorting wire carries no solved current: no ticks, one continuous buzz."""
    probe = probe_for(shorted_loop(), present=True, x=0.0, y=0.5, on="wire:0,3-0,1")
    assert probe.on == "wire:0,3-0,1"
    assert probe.buzz is True
    assert probe.pulse_hz == 0.0
    assert probe.current == 0.0


def test_probe_on_a_cool_wire_of_a_shorted_circuit_is_silent():
    """The top wire only leads to the bulb, so it is off the shorted path: no buzz."""
    probe = probe_for(shorted_loop(), present=True, x=0.2, y=0.1, on="wire:0,1-4,1")
    assert probe.on == "wire:0,1-4,1"
    assert (probe.buzz, probe.pulse_hz, probe.current) == (False, 0.0, 0.0)


def test_probe_does_not_mutate_the_circuit():
    circuit = solve_circuit(*one_bulb(), SOURCE_VOLTS)
    before = circuit.model_copy(deep=True)
    probe_for(circuit, present=True, x=0.4, y=0.5, on="A")
    assert circuit == before
