"""A mat's layout, and one reading of what is on it right now.

The paper is mostly fixed: printed parts and wires. The learner changes it in two ways
only: drawing a line where the mat invites one, and putting a tile in a slot. A reading
is therefore small (which lines are drawn, what is in each slot), whether it comes from
the camera or from a test.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contract import Dot, PartKind

SlotContent = Literal["empty", "wire", "bulb", "resistor", "switch"]


class _Strict(BaseModel):
    # A typo in a mat file should fail loudly at load time, not be ignored.
    model_config = ConfigDict(extra="forbid")


class Segment(_Strict):
    a: Dot
    b: Dot


class FixedPart(Segment):
    id: str
    kind: PartKind


class Drawable(Segment):
    """A line the learner may draw between two dots."""

    id: str


class Slot(Segment):
    """A place a tile can sit, joining two dots."""

    id: str
    accepts: list[SlotContent] = Field(min_length=1)
    starts: SlotContent = "empty"  # what the kit ships with in this slot


class MatLayout(_Strict):
    id: str
    cols: int = Field(ge=2)
    rows: int = Field(ge=2)
    battery_volts: float = Field(gt=0)
    parts: list[FixedPart] = []
    wires: list[Segment] = []
    drawables: list[Drawable] = []
    slots: list[Slot] = []

    @model_validator(mode="after")
    def _is_consistent(self) -> MatLayout:
        ids = [item.id for item in (*self.parts, *self.drawables, *self.slots)]
        if len(set(ids)) != len(ids):
            raise ValueError("part, drawable and slot ids must be unique across the mat")
        for item in (*self.parts, *self.wires, *self.drawables, *self.slots):
            for col, row in (item.a, item.b):
                if not (0 <= col < self.cols and 0 <= row < self.rows):
                    raise ValueError(f"dot {(col, row)} is off the {self.cols}x{self.rows} grid")
        for slot in self.slots:
            if slot.starts != "empty" and slot.starts not in slot.accepts:
                raise ValueError(f"slot {slot.id!r} starts with a tile it does not accept")
        return self

    def initial_reading(self) -> MatReading:
        """The mat as it comes out of the kit: nothing drawn, starting tiles in place."""
        return MatReading(slots={slot.id: slot.starts for slot in self.slots})


class MatReading(BaseModel):
    """What is on the mat right now. Frozen, so two readings can be compared cheaply."""

    model_config = ConfigDict(frozen=True)

    drawn: frozenset[str] = frozenset()  # ids of the drawables that have a line on them
    slots: dict[str, SlotContent] = {}  # slot id -> what sits in it; a missing slot is empty
