"""The state contract: every message between the server and the lab UI.

The server sends one `State` message about 15 times a second. The browser controls
voltage, mode, restart and reflection acknowledgement. Changes need the owner's sign-off;
after any change run `make contract` to refresh `contract/`.

The mat is a grid of dots. A Dot is [col, row], origin top-left. Every piece
lies on one segment: the gap between two dots that are neighbours in a row or a
column. A piece's id is its segment, "c,r-c,r" with the top-left dot first, so
the id stays the same while that piece stays where it is.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

# 2 (22 Nov 2026): touch.strength, piece.voltage, mode, lesson.reflection, and the browser's
# set_mode, restart_lesson and continue_lesson messages. Nothing was removed or renamed.
CONTRACT_VERSION = 2

Dot = tuple[int, int]

PieceType = Literal["wire", "battery", "bulb", "resistor", "switch"]
# working: current flows through at least one piece.
# open:    no complete loop through a battery (this includes an empty mat).
# shorted: a loop through a battery with nothing in it to resist the current.
CircuitStatus = Literal["working", "open", "shorted"]
Source = Literal["camera", "replay", "manual"]
Mode = Literal["tinker", "lab"]


def segment_id(a: Dot, b: Dot) -> str:
    """The id of the segment between two neighbouring dots, the same for either order."""
    first, second = sorted((a, b), key=lambda dot: (dot[1], dot[0]))
    return f"{first[0]},{first[1]}-{second[0]},{second[1]}"


# ---------- server -> browser ----------


class Grid(BaseModel):
    cols: int = Field(ge=2)  # dots across
    rows: int = Field(ge=2)  # dots down


class Piece(BaseModel):
    id: str  # segment_id(a, b)
    type: PieceType
    a: Dot  # for a battery, the positive end
    b: Dot
    closed: bool | None = None  # switches only: True lets current through
    current: float = 0.0  # amps, signed: positive flows a -> b
    voltage: float = 0.0  # volts across the piece; 0 for a wire and for a closed switch
    brightness: float | None = Field(None, ge=0.0, le=1.0)  # bulbs only; 1 is full
    shorted: bool = False  # this piece is on the shorted path

    @model_validator(mode="after")
    def _lies_on_one_segment(self) -> Piece:
        (ac, ar), (bc, br) = self.a, self.b
        if abs(ac - bc) + abs(ar - br) != 1:
            raise ValueError(f"piece ends {self.a} and {self.b} are not neighbouring dots")
        if self.id != segment_id(self.a, self.b):
            raise ValueError(f"piece id {self.id!r} does not match its ends")
        return self


class Circuit(BaseModel):
    status: CircuitStatus = "open"
    voltage: float = 0.0  # volts of every battery; the browser sets it
    total_current: float = 0.0  # amps leaving the battery, never negative
    shorted_path: list[str] = []  # piece ids round the shorted loop, in order; else empty


class Touch(BaseModel):
    """The learner's index fingertip, and what the mouse should do about it."""

    present: bool = False  # a fingertip is over the mat
    x: float = 0.0  # 0..1 from the first dot column to the last
    y: float = 0.0  # 0..1 from the first dot row to the last
    piece_id: str | None = None  # the piece under the fingertip, if any
    pulse_hz: float = 0.0  # tick rate to play on the mouse; 0 means silent
    # How hard to vibrate, 0 to 1: the current through the touched piece as a share of the
    # current that gets full strength. It rises and falls with pulse_hz. 1 while buzzing.
    strength: float = Field(0.0, ge=0.0, le=1.0)
    buzz: bool = False  # the touched piece is shorted: one hard continuous buzz, no ticks


class LessonStep(BaseModel):
    lesson_id: str = ""
    step_id: str = ""
    step_index: int = 0  # 0-based
    step_count: int = 0
    prompt: str = ""  # the text to show for this step
    step_done: bool = False  # latched after the circuit and touch goal holds for half a second
    lesson_done: bool = False  # every step has been completed
    reflection: str | None = None  # spoken question after the action; Continue advances it


class State(BaseModel):
    type: Literal["state"] = "state"
    version: int = CONTRACT_VERSION
    seq: int = 0  # goes up by one with every message
    t: float  # seconds since the server started
    source: Source = "camera"
    mode: Mode = "tinker"
    mat_visible: bool = True  # False while the camera cannot find the mat; pieces hold
    grid: Grid
    pieces: list[Piece] = []
    circuit: Circuit = Circuit()
    touch: Touch = Touch()
    lesson: LessonStep = LessonStep()


# ---------- browser -> server ----------

MAX_VOLTS = 9.0


class SetVoltage(BaseModel):
    """The scroll wheel's result: the battery voltage the learner wants."""

    type: Literal["set_voltage"] = "set_voltage"
    volts: float = Field(ge=0.0, le=MAX_VOLTS)


class RestartLesson(BaseModel):
    """Start again at step one and restore the demo's starting voltage."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["restart_lesson"] = "restart_lesson"


class SetMode(BaseModel):
    """Tinker preserves the circuit; entering Lab starts a fresh guided run at 3 V."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["set_mode"] = "set_mode"
    mode: Mode


class ContinueLesson(BaseModel):
    """The learner has finished reflecting out loud. This does not score their answer."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["continue_lesson"] = "continue_lesson"
    step_id: str


ClientMessage = Annotated[
    SetVoltage | RestartLesson | SetMode | ContinueLesson, Field(discriminator="type")
]
CLIENT_MESSAGE = TypeAdapter(ClientMessage)
