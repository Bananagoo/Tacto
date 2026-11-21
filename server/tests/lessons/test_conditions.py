"""A step's goal is checked against the solved circuit, one condition at a time."""

from tacto.contract import Circuit, Part
from tacto.lessons.conditions import LIT_THRESHOLD, is_satisfied
from tacto.lessons.models import DoneWhen


def bulb(part_id: str, brightness: float) -> Part:
    return Part(id=part_id, kind="bulb", a=(0, 0), b=(1, 0), brightness=brightness)


BATTERY = Part(id="battery", kind="battery", a=(0, 2), b=(1, 2))
# Two bulbs in one loop, both glowing.
SERIES = Circuit(
    status="closed",
    topology="series",
    parts=[BATTERY, bulb("bulb_a", 0.4), bulb("bulb_b", 0.4)],
)


def test_status_is_compared_with_the_circuit():
    assert is_satisfied(DoneWhen(status="closed"), SERIES)
    assert not is_satisfied(DoneWhen(status="open"), SERIES)


def test_topology_is_compared_with_the_circuit():
    assert is_satisfied(DoneWhen(topology="series"), SERIES)
    assert not is_satisfied(DoneWhen(topology="parallel"), SERIES)


def test_bulbs_counts_only_parts_that_are_bulbs():
    assert is_satisfied(DoneWhen(bulbs=2), SERIES)
    assert not is_satisfied(DoneWhen(bulbs=3), SERIES)  # the battery is not a bulb


def test_lit_bulbs_counts_bulbs_that_glow():
    one_lit = Circuit(status="closed", parts=[BATTERY, bulb("bulb_a", 0.8), bulb("bulb_b", 0.0)])

    assert is_satisfied(DoneWhen(lit_bulbs=1), one_lit)
    assert not is_satisfied(DoneWhen(lit_bulbs=2), one_lit)


def test_a_bulb_at_or_under_the_threshold_is_not_lit():
    dim = Circuit(parts=[bulb("at", LIT_THRESHOLD), bulb("under", LIT_THRESHOLD / 2)])
    glowing = Circuit(parts=[bulb("over", LIT_THRESHOLD + 0.01)])

    assert is_satisfied(DoneWhen(lit_bulbs=0), dim)
    assert is_satisfied(DoneWhen(lit_bulbs=1), glowing)


def test_every_condition_given_must_hold():
    everything = DoneWhen(status="closed", bulbs=2, lit_bulbs=2, topology="series")

    assert is_satisfied(everything, SERIES)


def test_one_unmet_condition_among_met_ones_fails():
    assert not is_satisfied(DoneWhen(status="closed", bulbs=2, topology="parallel"), SERIES)
    assert not is_satisfied(DoneWhen(status="closed", bulbs=1, topology="series"), SERIES)
    assert not is_satisfied(DoneWhen(status="short", bulbs=2, topology="series"), SERIES)
    assert not is_satisfied(DoneWhen(status="closed", bulbs=2, lit_bulbs=1), SERIES)


def test_an_empty_mat_satisfies_only_conditions_about_nothing():
    assert is_satisfied(DoneWhen(status="empty", bulbs=0, lit_bulbs=0, topology="none"), Circuit())
    assert not is_satisfied(DoneWhen(bulbs=1), Circuit())
