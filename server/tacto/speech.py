"""Opt-in speech relay. Audio and transcripts live only for this WebSocket session.

Silero in the browser commits speech segments; silence is not a completed answer.
Together's server VAD is disabled so every commit has one matching completed event.
No LLM calls, audio files, transcript logs, or credentials cross the browser boundary.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from contextlib import suppress
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

MODEL = "openai/whisper-large-v3"
BYTES_PER_SECOND = 16_000 * 2
MAX_SECONDS = 180
CONNECT_SECONDS = 15
FINALIZE_SECONDS = 15


class StartSpeech(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(pattern="^start$")
    step_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")


class SpeechError(Exception):
    """A safe message for the UI; never an upstream exception or response body."""


def together_connection(api_key: str):
    """Kept separate so tests substitute an in-memory provider, never paid inference."""
    query = urlencode(
        {
            "model": MODEL,
            "input_audio_format": "pcm_s16le_16000",
            "turn_detection": "none",
        }
    )
    return connect(
        f"wss://api.together.ai/v1/realtime?{query}",
        additional_headers={
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        },
        open_timeout=CONNECT_SECONDS,
        close_timeout=2,
        max_size=1_000_000,
        max_queue=16,
    )


async def _relay(socket: WebSocket, upstream, start: StartSpeech) -> None:
    async with asyncio.timeout(CONNECT_SECONDS):
        event = json.loads(await upstream.recv())
        if event.get("type") != "session.created":
            raise SpeechError(
                "Together could not start transcription. Check the server API key and access."
            )

    await socket.send_json({"type": "ready", "step_id": start.step_id})
    segments: list[str] = []
    partial = ""
    pending = 0
    audio_bytes = 0
    uncommitted_bytes = 0
    drained = asyncio.Event()
    drained.set()

    async def receive_transcripts() -> None:
        nonlocal partial, pending
        async for raw in upstream:
            event = json.loads(raw)
            kind = event.get("type")
            if kind == "conversation.item.input_audio_transcription.delta":
                # Together deltas replace the provisional phrase, unlike LLM token deltas.
                partial = str(event.get("delta", ""))
            elif kind == "conversation.item.input_audio_transcription.completed":
                if pending == 0:
                    raise SpeechError(
                        "Transcription returned an unexpected segment. Please try again."
                    )
                text = str(event.get("transcript", "")).strip()
                if text:
                    segments.append(text)
                partial = ""
                pending -= 1
                if pending == 0:
                    drained.set()
            elif kind in {"error", "conversation.item.input_audio_transcription.failed"}:
                raise SpeechError("Together could not transcribe this answer. Please try again.")
            else:
                continue
            await socket.send_json(
                {"type": "transcript", "text": " ".join(segments), "partial": partial}
            )
        raise SpeechError("The transcription connection ended early. Please try again.")

    async def receive_audio() -> None:
        nonlocal pending, audio_bytes, uncommitted_bytes
        while True:
            message = await socket.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()
            data = message.get("bytes")
            if data is not None:
                if not data or len(data) % 2 or len(data) > BYTES_PER_SECOND:
                    raise SpeechError("Invalid microphone audio. Please restart listening.")
                audio_bytes += len(data)
                uncommitted_bytes += len(data)
                if audio_bytes > MAX_SECONDS * BYTES_PER_SECOND:
                    raise SpeechError("This answer reached the three-minute recording limit.")
                await upstream.send(
                    json.dumps(
                        {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(data).decode(),
                        }
                    )
                )
                continue
            raw = message.get("text", "")
            if len(raw) > 1000:
                raise SpeechError("Invalid speech control.")
            control = json.loads(raw)
            if control == {"type": "commit"}:
                # A commit with nothing new to commit (two in a row) is passed over, not an
                # error: an empty buffer may never produce a completed event upstream.
                if uncommitted_bytes:
                    uncommitted_bytes = 0
                    pending += 1
                    drained.clear()
                    await upstream.send(json.dumps({"type": "input_audio_buffer.commit"}))
            elif control == {"type": "finish"}:
                # The browser commits the last voiced segment before finish. Do not commit
                # trailing silence: an empty buffer may never produce a completed event.
                async with asyncio.timeout(FINALIZE_SECONDS):
                    await drained.wait()
                if partial:
                    raise SpeechError("The final words were not finalized. Please try again.")
                await socket.send_json(
                    {"type": "answer", "step_id": start.step_id, "text": " ".join(segments)}
                )
                return
            else:
                raise SpeechError("Invalid speech control.")

    reader = asyncio.create_task(receive_transcripts())
    writer = asyncio.create_task(receive_audio())
    try:
        done, _ = await asyncio.wait({reader, writer}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        reader.cancel()
        writer.cancel()
        await asyncio.gather(reader, writer, return_exceptions=True)


def speech_router() -> APIRouter:
    router = APIRouter(prefix="/speech")

    @router.get("/status")
    def status() -> dict:
        # Configuration is not proof of account access. This endpoint does no inference.
        return {"configured": bool(os.getenv("TOGETHER_API_KEY", "").strip())}

    @router.websocket("/ws")
    async def speech(socket: WebSocket) -> None:
        # This demo is localhost-only. Block unrelated websites from using its paid relay.
        origin = urlsplit(socket.headers.get("origin", ""))
        if origin.scheme not in {"http", "https"} or origin.netloc != socket.headers.get("host"):
            await socket.close(code=1008)
            return
        await socket.accept()
        try:
            api_key = os.getenv("TOGETHER_API_KEY", "").strip()
            if not api_key:
                raise SpeechError("Speech is unavailable: add TOGETHER_API_KEY to the server .env.")
            async with asyncio.timeout(CONNECT_SECONDS):
                raw = await socket.receive_text()
                if len(raw) > 1000:
                    raise SpeechError("Invalid speech request.")
                start = StartSpeech.model_validate_json(raw)
            # No upstream connection is opened until the student's explicit start message.
            async with asyncio.timeout(MAX_SECONDS + CONNECT_SECONDS + FINALIZE_SECONDS):
                async with together_connection(api_key) as upstream:
                    await _relay(socket, upstream, start)
        except WebSocketDisconnect:
            return
        except SpeechError as error:
            with suppress(WebSocketDisconnect, RuntimeError, OSError):
                await socket.send_json({"type": "error", "message": str(error)})
        except TimeoutError:
            with suppress(WebSocketDisconnect, RuntimeError, OSError):
                await socket.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Transcription timed out. Your answer was not finalized. "
                            "Please try again."
                        ),
                    }
                )
        except (ValidationError, ValueError, TypeError):
            with suppress(WebSocketDisconnect, RuntimeError, OSError):
                await socket.send_json(
                    {"type": "error", "message": "Invalid speech request or provider response."}
                )
        except (WebSocketException, OSError):
            with suppress(WebSocketDisconnect, RuntimeError, OSError):
                await socket.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Cannot connect to Together. Check your connection, API key "
                            "and account access."
                        ),
                    }
                )
        finally:
            with suppress(WebSocketDisconnect, RuntimeError, OSError):
                await socket.close()

    return router
