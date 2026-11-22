"""The mock server: replays `contract/sample-states.jsonl` on /ws, looping for ever.

Run with `make mock`. It needs no camera, no mouse and no circuit solver, so it
behaves the same on every laptop. It reads `set_voltage` messages and checks
them, but a recording cannot react: the voltage in the replay does not change.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from tacto.contract import SetVoltage

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

        async def send_states() -> None:
            seq = 0
            while True:
                # The recording loops, but seq and t keep counting, as on the real server.
                state = recorded[seq % len(recorded)] | {"seq": seq, "t": round(seq / state_hz, 3)}
                await socket.send_text(json.dumps(state))
                seq += 1
                await asyncio.sleep(1 / state_hz)

        sender = asyncio.create_task(send_states())
        try:
            while True:
                raw = await socket.receive_text()
                try:
                    message = SetVoltage.model_validate_json(raw)
                    print(f"mock: set_voltage {message.volts} V (a replay does not react)")
                except ValidationError as err:
                    print(f"mock: bad client message: {raw!r}: {err.errors()[0]['msg']}")
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()

    return app


app = create_mock_app()
