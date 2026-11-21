"""Graph step: is there anything to solve, and where is the short?"""

from tacto.sim.graph import analyse

from .conftest import battery, bulb, one_bulb, part, two_in_series, wire


def test_empty_mat_is_empty():
    """No parts at all: nothing to classify, even if wires are drawn."""
    assert analyse([], []).status == "empty"
    assert analyse([], [wire((0, 1), (4, 1))]).status == "empty"


def test_battery_alone_is_open():
    """A battery with nothing between its terminals has no loop."""
    assert analyse([battery()], []).status == "open"


def test_no_battery_is_open():
    """A bulb and wires but no source: no current can flow."""
    assert analyse([bulb("A", (4, 1), (4, 3))], [wire((4, 1), (4, 3))]).status == "open"


def test_gap_in_the_loop_is_open():
    """The bottom wire stops one dot short of the battery, so the loop never closes."""
    parts, wires = one_bulb()
    wires[1] = wire((4, 3), (1, 3))
    assert analyse(parts, wires).status == "open"


def test_switch_opens_and_closes_the_loop():
    """A switch replaces half of the top wire; open breaks the loop, closed completes it."""
    parts, wires = one_bulb()
    wires[0] = wire((0, 1), (2, 1))
    open_switch = part("sw", "switch", (2, 1), (4, 1), closed=False)
    closed_switch = part("sw", "switch", (2, 1), (4, 1), closed=True)
    assert analyse([*parts, open_switch], wires).status == "open"
    assert analyse([*parts, closed_switch], wires).status == "closed"


def test_switch_with_unknown_state_is_treated_as_open():
    """Vision has not decided yet (closed=None): do not let current through on a guess."""
    parts, wires = one_bulb()
    wires[0] = wire((0, 1), (2, 1))
    undecided = part("sw", "switch", (2, 1), (4, 1))
    assert analyse([*parts, undecided], wires).status == "open"


def test_closed_loop_reports_the_dots_connected_to_the_battery():
    """Only the loop's four dots are live; a separate scribble elsewhere is not."""
    parts, wires = one_bulb()
    wires.append(wire((8, 8), (9, 8)))
    result = analyse(parts, wires)
    assert result.status == "closed"
    assert result.live_dots == {(0, 1), (4, 1), (4, 3), (0, 3)}
    assert result.overloaded_wires == frozenset()


def test_wire_straight_across_the_battery_is_short():
    """One wire from + to - : a zero-resistance path, and that wire is the hot one."""
    result = analyse([battery()], [wire((0, 1), (0, 3))])
    assert result.status == "short"
    assert result.overloaded_wires == {0}


def test_short_through_a_closed_switch_is_short():
    """Wires and a closed switch are all zero resistance; together they short the battery."""
    parts = [battery(), part("sw", "switch", (2, 1), (2, 3), closed=True)]
    wires = [wire((0, 1), (2, 1)), wire((2, 3), (0, 3))]
    result = analyse(parts, wires)
    assert result.status == "short"
    assert result.overloaded_wires == {0, 1}


def test_short_across_a_lit_two_bulb_circuit_names_only_the_shorted_path():
    """Two bulbs in series, then a wire drawn from (2,1) down to (2,3) and along to (0,3).

    Zero-resistance path between the terminals: (0,1) -> (2,1) [wire 0], (2,1) -> (2,3)
    [wire 2], (2,3) -> (0,3) [wire 3]. The bottom wire (4,3) -> (0,3) [wire 1] only leads
    to bulb A, and the stub (2,3) -> (2,5) [wire 4] leads nowhere, so neither is on the path.
    """
    parts, wires = two_in_series()
    wires += [wire((2, 1), (2, 3)), wire((2, 3), (0, 3)), wire((2, 3), (2, 5))]
    result = analyse(parts, wires)
    assert result.status == "short"
    assert result.overloaded_wires == {0, 2, 3}


def test_every_parallel_shorting_wire_is_overloaded():
    """Two wires drawn on the same pair of dots both carry the short."""
    result = analyse([battery()], [wire((0, 1), (0, 3)), wire((0, 3), (0, 1))])
    assert result.status == "short"
    assert result.overloaded_wires == {0, 1}


def test_degenerate_elements_are_ignored():
    """A wire from a dot to itself and a bulb with a == b join nothing, so they change nothing."""
    parts, wires = one_bulb()
    parts.append(bulb("dot", (4, 1), (4, 1)))
    wires.append(wire((0, 1), (0, 1)))
    assert analyse(parts, wires).status == "closed"


def test_battery_with_both_terminals_on_one_dot_is_not_a_source():
    """Misread battery (a == b): there is no source to drive a loop, so the mat is open."""
    parts = [part("bat", "battery", (0, 1), (0, 1)), bulb("A", (4, 1), (4, 3))]
    assert analyse(parts, [wire((0, 1), (4, 1))]).status == "open"
