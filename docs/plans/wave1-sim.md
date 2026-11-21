# Wave 1: simulation and haptics

**Owns:** `server/tacto/sim/`, `server/tests/test_sim_*.py`. Do not touch `web/src/haptics/` in this wave: tuning it needs the real mouse.

**Goal:** given the parts and wires read from the mat plus a source voltage, return a fully solved `Circuit` (contract model) and the pulse rate for any point on it.

## Reuse

- **networkx** (installed): connectivity, open-loop and short detection.
- **InSpice + ngspice** (installed; see the solver row in `docs/tech-stack.md`): the physics. Working call, checked on this project:

  ```python
  from InSpice.Spice.Netlist import Circuit
  from InSpice.Spice.Simulator import Simulator
  from InSpice.Unit import u_V, u_Ohm

  c = Circuit("one bulb")
  c.V("bat", "n0", c.gnd, 3 @ u_V)
  c.R("bulb", "n0", c.gnd, 10 @ u_Ohm)
  a = Simulator.factory().simulation(c, temperature=25, nominal_temperature=25).operating_point()
  float(a.branches["vbat"][0])  # -0.3: current is negative out of the source's + terminal
  ```

  `circuit.simulator()` from older PySpice examples raises "Deprecated API"; do not use it. The library is found through `NGSPICE_LIBRARY_PATH` (in `.env`). ngspice prints two startup warnings (no `spinit`, unsupported version 47); they are harmless.

## Tasks

1. **`sim/graph.py`**: build a graph from `Part`s and `Wire`s (dots joined by wires are one electrical node). Return a netlist plus a status: `empty` (no parts), `open` (no closed loop through the battery), `short` (a path across the battery with no bulb or resistor on it; an open switch breaks a path), `closed`.
2. **`sim/solver.py`**: one public function, netlist and source voltage in, per-part current and voltage out. Call ngspice only when the status is `closed`; SPICE cannot solve a floating or shorted circuit. Create the simulator once and reuse it. Bulbs are fixed resistors; put `BULB_OHMS` and `FULL_BRIGHT_AMPS` at the top of the file with a `TODO(sim owner)` note. A closed switch is a wire, an open one is a break. Parts not connected to the battery loop get zero current.
3. **`sim/feel.py`**: current in amps → `pulse_hz`, monotonic, 0 when no current. Constants at the top with `TODO(sim owner)`: the real maximum rate has to be felt on the mouse.
4. **`sim/__init__.py`**: one entry point, `solve_circuit(parts, wires, source_voltage) -> Circuit`, filling `status`, `total_current`, each part's `current`, `voltage` and `brightness`, and each wire's `current`.

## Tests (write first, hand-worked answer in each docstring)

- One bulb, 3 V: 0.3 A through everything.
- Two bulbs in series: half the current, half the voltage each.
- Two bulbs in parallel: each bulb gets the full voltage; battery current doubles.
- Open loop (missing wire, open switch): status `open`, all currents 0.
- Short (wire straight across the battery): status `short`.
- Raising the voltage raises `pulse_hz`; zero current gives 0.
- Signs: current direction on wires is consistent around the loop.

If `NGSPICE_LIBRARY_PATH` is unset or the library is missing, the tests must fail with a message that says to run `brew install libngspice`. Do not skip them.

## Done when

`make check` passes and `solve_circuit` returns the same numbers as `server/tacto/mock.py` for the mock's one-bulb layout.

## Needs a person

Feeling the pulse rate on the real mouse and setting the constants.
