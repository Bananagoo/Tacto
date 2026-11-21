"""Tacto server. Run with `make server` (uvicorn tacto.main:app --reload --port 8000).

TACTO_SOURCE picks where the world comes from:
  mock    fake circuit, no hardware (default)
  replay  recorded frames from server/fixtures/   (not built yet)
  camera  the LogiInsight camera                  (not built yet)
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from .contract import ClientMessage
from .devtools import router as devtools_router
from .mock import MockWorld

load_dotenv()

SOURCE = os.getenv("TACTO_SOURCE", "mock")
STATE_HZ = 15

app = FastAPI(title="Tacto")
app.include_router(devtools_router)  # hardware test bench, see devtools.py
_client_message = TypeAdapter(ClientMessage)


def make_world():
    if SOURCE == "mock":
        return MockWorld()
    raise NotImplementedError(f"TACTO_SOURCE={SOURCE} is not built yet; see docs/architecture.md")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "source": SOURCE}


@app.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    await socket.accept()
    world = make_world()

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
                print(f"bad client message: {raw!r}: {err.errors()[0]['msg']}")
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
