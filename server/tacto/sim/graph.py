"""The electrical graph of the mat: is there anything to solve, and where is a short?

Every dot is a node. Wires and closed switches join dots with no resistance; bulbs and
resistors join them with resistance; an open switch joins nothing. This step runs before
the solver so that ngspice only ever sees a circuit with a unique answer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import networkx as nx

from tacto.contract import CircuitStatus, Dot, Part, Wire


@dataclass(frozen=True)
class GraphAnalysis:
    """What the graph says about the mat before any numbers are computed."""

    status: CircuitStatus
    # The source driving the circuit, when there is one.
    battery: Part | None = None
    # Indexes into `wires` of every wire on a zero-resistance path between the terminals.
    overloaded_wires: frozenset[int] = frozenset()
    # Dots with a conducting path to the battery. Only set when the status is "closed".
    live_dots: frozenset[Dot] = frozenset()


def joins_two_dots(element: Part | Wire) -> bool:
    """False for a wire or part whose ends sit on one dot: it connects nothing."""
    return element.a != element.b


def is_zero_resistance(part: Part) -> bool:
    """A closed switch conducts like a wire. An unread switch (closed=None) counts as open."""
    return part.kind == "switch" and part.closed is True and joins_two_dots(part)


def is_resistive(part: Part) -> bool:
    return part.kind in ("bulb", "resistor") and joins_two_dots(part)


def find_battery(parts: Sequence[Part]) -> Part | None:
    """The one source the circuit runs from.

    The kit has a single battery. If vision reports several, the lowest id wins so the
    answer does not depend on the order of `parts`; the others are treated as breaks.
    """
    batteries = [p for p in parts if p.kind == "battery" and joins_two_dots(p)]
    return min(batteries, key=lambda p: p.id, default=None)


def analyse(parts: Sequence[Part], wires: Sequence[Wire]) -> GraphAnalysis:
    """Classify the mat as empty, open, short or closed."""
    if not parts:
        return GraphAnalysis(status="empty")
    battery = find_battery(parts)
    if battery is None:
        return GraphAnalysis(status="open")

    zero_ohm = _zero_resistance_graph(parts, wires)
    if _connected(zero_ohm, battery.a, battery.b):
        overloaded = _wires_between(zero_ohm, wires, battery.a, battery.b)
        return GraphAnalysis(status="short", battery=battery, overloaded_wires=overloaded)

    conducting = zero_ohm.copy()
    conducting.add_edges_from((p.a, p.b) for p in parts if is_resistive(p))
    if not _connected(conducting, battery.a, battery.b):
        return GraphAnalysis(status="open", battery=battery)
    live_dots = frozenset(nx.node_connected_component(conducting, battery.a))
    return GraphAnalysis(status="closed", battery=battery, live_dots=live_dots)


def _zero_resistance_graph(parts: Sequence[Part], wires: Sequence[Wire]) -> nx.Graph:
    # A simple graph is enough here: two wires on the same pair of dots connect them
    # exactly as one does.
    graph = nx.Graph()
    graph.add_edges_from((w.a, w.b) for w in wires if joins_two_dots(w))
    graph.add_edges_from((p.a, p.b) for p in parts if is_zero_resistance(p))
    return graph


def _connected(graph: nx.Graph, a: Dot, b: Dot) -> bool:
    return a in graph and b in graph and nx.has_path(graph, a, b)


def _wires_between(
    zero_ohm: nx.Graph, wires: Sequence[Wire], positive: Dot, negative: Dot
) -> frozenset[int]:
    """Indexes of the wires that lie on some zero-resistance path between the terminals.

    An edge is on a simple path from `positive` to `negative` exactly when it shares a
    cycle with a direct edge between them. So add that edge and take its biconnected
    component: dead-end stubs and side loops fall into other components.
    """
    with_battery = zero_ohm.copy()
    with_battery.add_edge(positive, negative)
    shorted_edges: set[frozenset[Dot]] = set()
    for component in nx.biconnected_component_edges(with_battery):
        edges = {frozenset(edge) for edge in component}
        if frozenset((positive, negative)) in edges:
            shorted_edges = edges
            break
    return frozenset(
        index for index, w in enumerate(wires) if frozenset((w.a, w.b)) in shorted_edges
    )
