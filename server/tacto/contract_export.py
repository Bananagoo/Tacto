"""Write the contract's JSON schemas and an example message for the UI team.

Run with `make contract`. The files land in `contract/` at the repo root and are
committed, so the UI team never needs the Python side to read the contract.
"""

from __future__ import annotations

import json
from pathlib import Path

from tacto.contract import (
    AnswerReflection,
    Circuit,
    ContinueLesson,
    Grid,
    LessonStep,
    Piece,
    RestartLesson,
    SetMode,
    SetVoltage,
    State,
    Touch,
    segment_id,
)

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contract"


def example_state() -> State:
    """One bulb on a closed loop at 6 V, with a fingertip resting on the bulb.

    Hand-worked: the bulb is 10 ohms, so 6 V drives 0.6 A round the loop, which
    is the bulb's full brightness and a 3 Hz pulse.
    """
    loop: list[tuple[str, tuple[int, int], tuple[int, int]]] = [
        ("battery", (1, 1), (1, 2)),  # positive end up
        ("wire", (1, 1), (2, 1)),
        ("bulb", (2, 1), (3, 1)),
        ("wire", (3, 1), (3, 2)),
        ("wire", (3, 2), (2, 2)),
        ("wire", (2, 2), (1, 2)),
    ]
    pieces = [
        Piece(
            id=segment_id(a, b),
            type=kind,  # type: ignore[arg-type]
            a=a,
            b=b,
            # Current leaves the battery's positive end, so inside the battery it runs b -> a.
            current=-0.6 if kind == "battery" else 0.6,
            brightness=1.0 if kind == "bulb" else None,
        )
        for kind, a, b in loop
    ]
    return State(
        seq=412,
        t=27.4,
        source="manual",
        mode="lab",
        grid=Grid(cols=9, rows=6),
        pieces=pieces,
        circuit=Circuit(status="working", voltage=6.0, total_current=0.6),
        touch=Touch(present=True, x=0.31, y=0.2, piece_id="2,1-3,1", pulse_hz=3.0),
        lesson=LessonStep(
            lesson_id="circuits-101",
            step_id="raise_voltage",
            step_index=3,
            step_count=6,
            prompt="Keep your finger there. Turn the wheel up to 6 V.",
            step_done=True,
            reflection="Why did the pulse get faster when you raised the voltage?",
        ),
    )


def contract_files() -> dict[str, str]:
    """File name -> contents for everything in `contract/`."""

    def dump(data: object) -> str:
        return json.dumps(data, indent=2) + "\n"

    return {
        "state.schema.json": dump(State.model_json_schema()),
        "set_voltage.schema.json": dump(SetVoltage.model_json_schema()),
        "restart_lesson.schema.json": dump(RestartLesson.model_json_schema()),
        "set_mode.schema.json": dump(SetMode.model_json_schema()),
        "continue_lesson.schema.json": dump(ContinueLesson.model_json_schema()),
        "answer_reflection.schema.json": dump(AnswerReflection.model_json_schema()),
        "example-state.json": dump(example_state().model_dump(mode="json")),
        "example-set-voltage.json": dump(SetVoltage(volts=6.5).model_dump(mode="json")),
        "example-restart-lesson.json": dump(RestartLesson().model_dump(mode="json")),
        "example-set-mode.json": dump(SetMode(mode="lab").model_dump(mode="json")),
        "example-continue-lesson.json": dump(
            ContinueLesson(step_id="raise_voltage").model_dump(mode="json")
        ),
        "example-answer-reflection.json": dump(
            AnswerReflection(step_id="raise_voltage", text="more push so more flow").model_dump(
                mode="json"
            )
        ),
    }


def main() -> None:
    CONTRACT_DIR.mkdir(exist_ok=True)
    for name, text in contract_files().items():
        (CONTRACT_DIR / name).write_text(text)
        print(f"contract_export: wrote contract/{name}")


if __name__ == "__main__":
    main()
