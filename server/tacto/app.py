"""The web app: one WebSocket that streams State and takes the learner's messages."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from .contract import ClientMessage
from .world import WorldFactory

STATE_HZ = 15
DEFAULT_NICKNAME = "guest"

_client_message = TypeAdapter(ClientMessage)


def create_app(make_world: WorldFactory, *, source: str) -> FastAPI:
    """Build the app around a world. `source` is reported by /health for the people running it."""
    app = FastAPI(title="Tacto")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "source": source}

    @app.websocket("/ws")
    async def ws(socket: WebSocket, learner: str = DEFAULT_NICKNAME) -> None:
        await socket.accept()
        # The page passes ?learner=<nickname>; there is no login and no text box.
        world = make_world(learner)

        async def send_states() -> None:
            while True:
                await socket.send_text(world.state().model_dump_json())
                await asyncio.sleep(1 / STATE_HZ)

        sender = asyncio.create_task(send_states())
        try:
            while True:
                raw = await socket.receive_text()
                try:
                    world.handle(_client_message.validate_json(raw))
                except ValidationError as err:
                    print(f"app: bad client message: {raw!r}: {err.errors()[0]['msg']}")
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()

    return app
