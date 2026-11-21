"""The test bench circuit from the plan, and small helpers to vary it.

Dots are (col, row). The base loop is:

    (0,1) ---- top wire ---- (4,1)
      |                        |
    battery                  bulb A
      |                        |
    (0,3) --- bottom wire -- (4,3)

The battery's `a` (positive terminal) is (0,1). Bulbs are 10 ohms.
"""

from tacto.contract import Dot, Part, PartKind, Wire

SOURCE_VOLTS = 6.0


def battery() -> Part:
    return Part(id="bat", kind="battery", a=(0, 1), b=(0, 3))


def part(part_id: str, kind: PartKind, a: Dot, b: Dot, *, closed: bool | None = None) -> Part:
    return Part(id=part_id, kind=kind, a=a, b=b, closed=closed)


def bulb(part_id: str, a: Dot, b: Dot) -> Part:
    return part(part_id, "bulb", a, b)


def wire(a: Dot, b: Dot) -> Wire:
    return Wire(a=a, b=b)


def one_bulb() -> tuple[list[Part], list[Wire]]:
    """Battery, top wire, bulb A, bottom wire: a single loop."""
    parts = [battery(), bulb("A", (4, 1), (4, 3))]
    wires = [wire((0, 1), (4, 1)), wire((4, 3), (0, 3))]
    return parts, wires


def two_in_series() -> tuple[list[Part], list[Wire]]:
    """Bulb B replaces part of the top wire, so the same current runs through A and B."""
    parts = [battery(), bulb("B", (2, 1), (4, 1)), bulb("A", (4, 1), (4, 3))]
    wires = [wire((0, 1), (2, 1)), wire((4, 3), (0, 3))]
    return parts, wires


def two_in_parallel() -> tuple[list[Part], list[Wire]]:
    """Bulb B sits on its own branch from (4,1) to (4,3), beside bulb A.

    The branch goes out to column 6 and back: (4,1) -> (6,1), bulb B (6,1) -> (6,3),
    (6,3) -> (4,3). The junctions are the dots (4,1) and (4,3).
    """
    parts, wires = one_bulb()
    parts.append(bulb("B", (6, 1), (6, 3)))
    wires += [wire((4, 1), (6, 1)), wire((6, 3), (4, 3))]
    return parts, wires
