"""A spoken answer: one clip in, a transcript out, handed on like a typed answer.

The browser decides when the learner has finished speaking (voice detection runs there)
and sends that stretch of sound as one WAV file. It is transcribed through Together and
given to the lab as an `answer_reflection`, the same message a typed answer sends, so
there is one path for grading and for what happens next.

A clip that cannot be transcribed becomes an empty answer. That is graded "unclear", so
the question is asked again instead of anything going wrong (docs/voice-reflections-plan.md).
Clips are not kept: the audio lives for the length of this request.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Protocol

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from tacto import voice_models
from tacto.contract import AnswerReflection, ClientMessage

# About 30 s of 16 kHz mono as 32-bit samples, which is what the browser's detector sends.
# The page stops listening after 15 s, so anything larger is not an answer.
MAX_CLIP_BYTES = 2_000_000
MAX_ANSWER_CHARS = 2000
TIMEOUT_S = 8.0
# Words to expect, which a transcriber otherwise mishears ("currant", "volt edge").
VOCABULARY = "An electric circuit: battery, bulb, wire, switch, voltage, current, resistance."

Transcriber = Callable[[bytes], str]


class TakesAnswers(Protocol):
    def handle(self, message: ClientMessage) -> None: ...


def transcribe(wav: bytes, client: httpx.Client) -> str:
    """What was said in one WAV clip, from Together. Raises on any failure."""
    response = client.post(
        "/audio/transcriptions",
        # The docs ask for the model field before the file.
        data={
            "model": voice_models.STT_MODEL,
            "language": "en",
            "response_format": "json",
            "prompt": VOCABULARY,
        },
        files={"file": ("answer.wav", wav, "audio/wav")},
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    return str(response.json()["text"]).strip()


def answer_router(lab: TakesAnswers, transcriber: Transcriber | None) -> APIRouter:
    """POST /voice/answer?step_id=...: a WAV clip of the learner's answer."""
    router = APIRouter()

    @router.post("/voice/answer")
    async def answer(request: Request, step_id: str = Query(min_length=1, max_length=100)) -> dict:
        declared = int(request.headers.get("content-length") or 0)
        if declared > MAX_CLIP_BYTES:
            raise HTTPException(status_code=413, detail="the clip is too long")
        wav = await request.body()
        if len(wav) > MAX_CLIP_BYTES:
            raise HTTPException(status_code=413, detail="the clip is too long")
        if not wav.startswith(b"RIFF"):
            raise HTTPException(status_code=400, detail="the clip is not a WAV file")
        started = time.perf_counter()
        text, transcribed = "", False
        if transcriber is not None:
            try:
                text = (await asyncio.to_thread(transcriber, wav))[:MAX_ANSWER_CHARS]
                transcribed = True
            except Exception as error:  # noqa: BLE001 - whatever went wrong, ask again
                print(f"listen: a clip could not be transcribed: {type(error).__name__}")
        taken_ms = round((time.perf_counter() - started) * 1000)
        lab.handle(AnswerReflection(step_id=step_id, text=text))
        return {"text": text, "transcribed": transcribed, "transcribe_ms": taken_ms}

    return router
