"""The contract between server and web. Single source of truth.

Every message on the WebSocket is one of these models as JSON. If you change
anything here, change web/src/contract.ts in the same commit and tell the team.

Coordinates: a Dot is (col, row) on the mat's dot grid, origin top-left.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Dot = tuple[int, int]

PartKind = Literal["battery", "bulb", "resistor", "switch"]
CircuitStatus = Literal["empty", "open", "closed", "short"]
Concept = Literal["closed_loop", "current", "voltage", "resistance", "series", "parallel"]
Mastery = Literal["unseen", "shaky", "solid"]
Zone = Literal["too_easy", "productive", "stuck"]
Phase = Literal["build", "predict", "test", "explain", "done"]
HapticPattern = Literal["tick", "nudge", "short", "success"]


# ---------- server -> web ----------


class Part(BaseModel):
    id: str
    kind: PartKind
    a: Dot
    b: Dot
    closed: bool | None = None  # switches only
    current: float = 0.0  # amps, signed a -> b
    voltage: float = 0.0  # volts across the part
    brightness: float = Field(0.0, ge=0.0, le=1.0)  # bulbs only


class Wire(BaseModel):
    a: Dot
    b: Dot
    current: float = 0.0  # amps, signed a -> b


class Circuit(BaseModel):
    status: CircuitStatus = "empty"
    source_voltage: float = 0.0  # set by the scroll wheel
    total_current: float = 0.0
    parts: list[Part] = []
    wires: list[Wire] = []


class Probe(BaseModel):
    """Where the learner's fingertip is, and what the mouse should do about it."""

    present: bool = False
    x: float = 0.0  # mat coordinates, 0..1 from the left
    y: float = 0.0  # mat coordinates, 0..1 from the top
    on: str | None = None  # part id, or "wire:c,r-c,r", or None
    current: float = 0.0
    pulse_hz: float = 0.0  # tick rate for the mouse; 0 means silent


class Tutor(BaseModel):
    challenge_id: str = ""
    phase: Phase = "build"
    prompt: str = ""
    choices: list[str] = []  # non-empty only in the predict phase
    audio_url: str | None = None
    zone: Zone = "productive"
    score: int = 0


class State(BaseModel):
    type: Literal["state"] = "state"
    t: float
    source: Literal["mock", "replay", "camera"] = "mock"
    circuit: Circuit = Circuit()
    probe: Probe = Probe()
    tutor: Tutor = Tutor()
    learner: dict[Concept, Mastery] = {}


class Haptic(BaseModel):
    """One-off effect chosen by the server, e.g. the tutor's nudge."""

    type: Literal["haptic"] = "haptic"
    pattern: HapticPattern


ServerMessage = Annotated[State | Haptic, Field(discriminator="type")]


# ---------- web -> server ----------


class Wheel(BaseModel):
    type: Literal["wheel"] = "wheel"
    steps: int  # positive = more voltage


class Answer(BaseModel):
    type: Literal["answer"] = "answer"
    choice: str
    via: Literal["voice", "button"] = "button"


class CalibrateTouch(BaseModel):
    """The learner is touching corner marker `corner` right now (0=TL,1=TR,2=BR,3=BL)."""

    type: Literal["calibrate_touch"] = "calibrate_touch"
    corner: Literal[0, 1, 2, 3]


class Next(BaseModel):
    type: Literal["next"] = "next"


ClientMessage = Annotated[Wheel | Answer | CalibrateTouch | Next, Field(discriminator="type")]
