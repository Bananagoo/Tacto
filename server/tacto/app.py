"""One WebSocket streams state and accepts voltage, mode and lesson controls."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from tacto.contract import CLIENT_MESSAGE
from tacto.lab import Lab

STATE_HZ = 15


def create_lab_app(lab: Lab, *, source: str, state_hz: float = STATE_HZ) -> FastAPI:
    """Build the app round a lab. `source` is reported by /health for the people running it."""
    app = FastAPI(title="Tacto")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "source": source}

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()

        async def send_states() -> None:
            while True:
                # The solver can take a few milliseconds; keep it off the event loop.
                state = await asyncio.to_thread(lab.state)
                await socket.send_text(state.model_dump_json())
                await asyncio.sleep(1 / state_hz)

        sender = asyncio.create_task(send_states())
        try:
            while True:
                raw = await socket.receive_text()
                try:
                    lab.handle(CLIENT_MESSAGE.validate_json(raw))
                except ValidationError as err:
                    print(f"app: bad client message: {raw!r}: {err.errors()[0]['msg']}")
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()

    return app
