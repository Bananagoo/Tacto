"""Does the circuit on the mat satisfy a step's goal?"""

from __future__ import annotations

from ..contract import Circuit
from .models import DoneWhen

# A bulb this dim looks off on screen, so it must not count as lit for a lesson goal.
# TODO(lesson owner): confirm against the solver's brightness curve once bulbs are tuned.
LIT_THRESHOLD = 0.02


def is_satisfied(done_when: DoneWhen, circuit: Circuit) -> bool:
    """True when every condition the step gives holds. Conditions left out are not checked."""
    bulbs = [part for part in circuit.parts if part.kind == "bulb"]
    lit_bulbs = [bulb for bulb in bulbs if bulb.brightness > LIT_THRESHOLD]
    wanted_and_found = (
        (done_when.status, circuit.status),
        (done_when.topology, circuit.topology),
        (done_when.bulbs, len(bulbs)),
        (done_when.lit_bulbs, len(lit_bulbs)),
    )
    return all(wanted is None or wanted == found for wanted, found in wanted_and_found)
