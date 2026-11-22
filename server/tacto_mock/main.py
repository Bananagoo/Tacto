"""The mock server: replays `contract/sample-states.jsonl` on /ws, looping for ever.

Run with `make mock`. It needs no camera, no mouse and no circuit solver, so it
behaves the same on every laptop. Mode, restart and reflection controls work;
the recorded voltage does not react to `set_voltage`.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from tacto.contract import (
    CLIENT_MESSAGE,
    AnswerReflection,
    ContinueLesson,
    LessonStep,
    ReflectionHeard,
    RestartLesson,
    SetMode,
)

from .sample import SAMPLE_PATH

STATE_HZ = 15


def create_mock_app(sample_path: Path = SAMPLE_PATH, *, state_hz: float = STATE_HZ) -> FastAPI:
    recorded = [json.loads(line) for line in sample_path.read_text().splitlines() if line]
    if not recorded:
        raise RuntimeError(f"{sample_path} holds no states. Run: make sample")
    app = FastAPI(title="Tacto mock")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "source": "replay", "states": len(recorded)}

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()
        cursor = 0
        mode = "lab"

        async def send_states() -> None:
            nonlocal cursor
            seq = 0
            while True:
                # The recording loops, but seq and t keep counting, as on the real server.
                frame = recorded[cursor]
                state = frame | {"seq": seq, "t": round(seq / state_hz, 3), "mode": mode}
                if mode == "tinker":
                    state["lesson"] = LessonStep().model_dump(mode="json")
                await socket.send_text(json.dumps(state))
                if mode != "lab" or not frame["lesson"].get("reflection"):
                    cursor = (cursor + 1) % len(recorded)
                seq += 1
                await asyncio.sleep(1 / state_hz)

        sender = asyncio.create_task(send_states())
        try:
            while True:
                raw = await socket.receive_text()
                try:
                    message = CLIENT_MESSAGE.validate_json(raw)
                    if isinstance(message, RestartLesson):
                        cursor, mode = 0, "lab"
                    elif isinstance(message, SetMode):
                        if message.mode == "lab" and mode != "lab":
                            cursor = 0
                        mode = message.mode
                    elif isinstance(message, ContinueLesson):
                        current = recorded[cursor]["lesson"]
                        if (
                            mode == "lab"
                            and current.get("reflection")
                            and current["step_id"] == message.step_id
                        ):
                            cursor = next(
                                (
                                    i
                                    for i in range(cursor + 1, len(recorded))
                                    if recorded[i]["lesson"]["step_id"] != message.step_id
                                    or recorded[i]["lesson"]["lesson_done"]
                                ),
                                cursor,
                            )
                    elif isinstance(message, ReflectionHeard):
                        pass  # a replay has no lines to speak
                    elif isinstance(message, AnswerReflection):
                        print(f"mock: answer to {message.step_id!r} (a replay does not grade)")
                    else:
                        print(f"mock: set_voltage {message.volts} V (a replay does not react)")
                except ValidationError as err:
                    print(f"mock: bad client message: {raw!r}: {err.errors()[0]['msg']}")
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()

    return app


load_dotenv()
app = create_mock_app()
