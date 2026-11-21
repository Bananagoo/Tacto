"""Turn a mat's layout and one reading of it into the parts and wires of a circuit."""

from __future__ import annotations

from ..contract import Part, Wire
from .models import MatLayout, MatReading


def compose(layout: MatLayout, reading: MatReading) -> tuple[list[Part], list[Wire]]:
    """The circuit on the mat, unsolved: every current and voltage is still zero.

    Raises ValueError for a reading that does not fit the layout (an unknown id, or a tile
    its slot does not accept): that is a bug in whatever produced the reading.
    """
    drawable_ids = {drawable.id for drawable in layout.drawables}
    slot_ids = {slot.id for slot in layout.slots}
    unknown = (reading.drawn - drawable_ids) | (set(reading.slots) - slot_ids)
    if unknown:
        raise ValueError(f"reading names things this mat does not have: {sorted(unknown)}")

    parts = [Part(id=part.id, kind=part.kind, a=part.a, b=part.b) for part in layout.parts]
    wires = [Wire(a=wire.a, b=wire.b) for wire in layout.wires]
    wires += [Wire(a=d.a, b=d.b) for d in layout.drawables if d.id in reading.drawn]

    for slot in layout.slots:
        content = reading.slots.get(slot.id, "empty")
        if content == "empty":
            continue
        if content not in slot.accepts:
            raise ValueError(f"slot {slot.id!r} does not accept a {content}")
        if content == "wire":
            wires.append(Wire(a=slot.a, b=slot.b))
        else:
            parts.append(
                Part(
                    id=f"{content}@{slot.id}",
                    kind=content,
                    a=slot.a,
                    b=slot.b,
                    # A switch tile is a closed one; an open switch is an empty slot.
                    closed=True if content == "switch" else None,
                )
            )
    return parts, wires
