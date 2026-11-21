"""The one place that talks to ngspice: a resistor netlist in, node voltages out.

The caller must hand over a circuit with a unique answer: every node reachable from
the source through resistors, and no zero-ohm element. `graph.py` guarantees that.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

LIBRARY_PATH_VARIABLE = "NGSPICE_LIBRARY_PATH"
# Where Homebrew (Apple silicon, Intel) and Debian/Ubuntu put the shared library.
LIBRARY_SEARCH_PATHS: tuple[str, ...] = (
    "/opt/homebrew/lib/libngspice.dylib",
    "/usr/local/lib/libngspice.dylib",
    "/usr/lib/x86_64-linux-gnu/libngspice.so.0",
)
# ngspice's name for the reference node. The source's negative terminal sits here.
GROUND = "0"
SOURCE_NAME = "bat"
# Circuit temperature. Our resistors do not drift with it; ngspice just needs a value.
TEMPERATURE_CELSIUS = 25


class NgspiceNotFoundError(RuntimeError):
    """The ngspice shared library is not installed where we can find it."""


@dataclass(frozen=True, order=True)
class Resistor:
    """One resistance between two named nodes. Node names are lowercase, e.g. "n4_1"."""

    node_a: str
    node_b: str
    ohms: float


def find_ngspice_library(environ: Mapping[str, str]) -> str:
    """Path of the ngspice shared library, from the environment or the usual places."""
    configured = environ.get(LIBRARY_PATH_VARIABLE)
    if configured is not None:
        if not os.path.exists(configured):
            raise NgspiceNotFoundError(
                f"{LIBRARY_PATH_VARIABLE} is set to {configured!r}, which does not exist. "
                "Unset it, or run: brew install libngspice"
            )
        return configured
    for path in LIBRARY_SEARCH_PATHS:
        if os.path.exists(path):
            return path
    raise NgspiceNotFoundError(
        "The circuit solver needs ngspice and could not find it. Run: brew install libngspice "
        f"(or set {LIBRARY_PATH_VARIABLE} to the library file)."
    )


def solve_node_voltages(
    source_voltage: float, positive_node: str, resistors: Sequence[Resistor]
) -> dict[str, float]:
    """Run one DC operating point and return the voltage of every node, ground included.

    The source drives `positive_node` to `source_voltage` above `GROUND`.
    """
    # ngspice is a single shared instance and not thread-safe, so one solve at a time.
    with _lock:
        simulator = _shared_simulator()
        netlist = _build_netlist(source_voltage, positive_node, resistors)
        analysis = simulator.simulation(
            netlist, temperature=TEMPERATURE_CELSIUS, nominal_temperature=TEMPERATURE_CELSIUS
        ).operating_point()
        volts = {name: float(waveform[0]) for name, waveform in analysis.nodes.items()}
        # ngspice keeps every circuit it is given. The loop solves many times a second,
        # so drop this one or memory grows by about 100 MB every ten minutes.
        simulator.ngspice.remove_circuit()
    volts[GROUND] = 0.0
    return volts


_lock = threading.Lock()
_simulator: Any = None


def _shared_simulator() -> Any:
    """Create the simulator on first use. Call with `_lock` held."""
    global _simulator
    if _simulator is None:
        # InSpice reads this variable when it first loads, so set it before the import.
        os.environ[LIBRARY_PATH_VARIABLE] = find_ngspice_library(os.environ)
        from InSpice.Spice.Simulator import Simulator

        _simulator = Simulator.factory()
    return _simulator


def _build_netlist(source_voltage: float, positive_node: str, resistors: Sequence[Resistor]) -> Any:
    # Imported here, after `_shared_simulator` has pointed InSpice at the library, and so
    # that importing this module never needs ngspice.
    from InSpice.Spice.Netlist import Circuit as SpiceCircuit
    from InSpice.Unit import u_Ohm, u_V

    netlist = SpiceCircuit("tacto")
    netlist.V(SOURCE_NAME, positive_node, GROUND, source_voltage @ u_V)
    # Sorted so the same circuit always produces the same netlist, whatever order the
    # mat was read in.
    for index, resistor in enumerate(sorted(resistors)):
        netlist.R(index, resistor.node_a, resistor.node_b, resistor.ohms @ u_Ohm)
    return netlist
