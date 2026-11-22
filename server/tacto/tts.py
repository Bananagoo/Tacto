"""The lab's voice: every line it can say, spoken once and kept on disk.

Nothing is synthesised while a learner is at the mat. At startup each line the lesson
file holds for a reflection (the questions, the confirmations, the ideas stated at the
exit) is looked up in a folder of audio files, named by a hash of the words, the voice
and the model. Only lines that are not there are sent to Together. A second start asks
for nothing, and with the network down whatever is on disk still plays.

Rewording a line in the lesson file makes a new file; the old one is left behind.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from tacto import voice_models
from tacto.lesson import Lesson

CACHE_DIR = Path(__file__).resolve().parents[1] / "voice_cache"
URL_PREFIX = "/voice"
# One line of speech takes a second or so; this is generous, and only matters at startup.
TIMEOUT_S = 30.0
_NAME = re.compile(r"^[0-9a-f]{24}\.wav$")

Synthesiser = Callable[[str], bytes]


def lines_of(lesson: Lesson) -> list[str]:
    """Every line the lab says aloud, once each, in lesson order."""
    lines: list[str] = []
    for step in lesson.steps:
        asked = step.funnel
        if asked is None:
            continue
        lines += [level.question for level in asked.levels]
        lines += [asked.confirmation]
        lines += [level.confirmation for level in asked.levels if level.confirmation]
        lines += [asked.exit.line]
    return list(dict.fromkeys(lines))


def file_name(line: str) -> str:
    """The cache file for a line said in the configured voice by the configured model."""
    spoken_as = f"{voice_models.TTS_MODEL}\n{voice_models.TTS_VOICE}\n{line}"
    return hashlib.sha256(spoken_as.encode()).hexdigest()[:24] + ".wav"


def url_for(name: str) -> str:
    return f"{URL_PREFIX}/{name}"


def synthesise(line: str, client: httpx.Client) -> bytes:
    """One line as a WAV file, from Together. Raises on any failure."""
    response = client.post(
        "/audio/speech",
        json={
            "model": voice_models.TTS_MODEL,
            "input": line,
            "voice": voice_models.TTS_VOICE,
            "response_format": "wav",
        },
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    return response.content


def ensure_cached(
    lines: list[str], cache_dir: Path, synthesiser: Synthesiser | None
) -> dict[str, str]:
    """Line -> the name of its audio file, for every line that has one.

    Lines already on disk are found without a call. The rest are synthesised if there
    is a `synthesiser`; one that fails is left out and will only be shown, not spoken.
    """
    cached: dict[str, str] = {}
    spoken = 0
    for line in lines:
        name = file_name(line)
        path = cache_dir / name
        if not path.is_file():
            if synthesiser is None:
                continue
            try:
                audio = synthesiser(line)
            except (httpx.HTTPError, OSError, ValueError) as error:
                print(f"tts: could not speak {line[:40]!r}: {type(error).__name__}")
                continue
            if not audio.startswith(b"RIFF"):
                print(f"tts: the reply for {line[:40]!r} was not a WAV file; not kept")
                continue
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Written whole or not at all: a start cut short must not leave half a file.
            partial = path.with_suffix(".part")
            partial.write_bytes(audio)
            partial.replace(path)
            spoken += 1
        cached[line] = name
    print(f"tts: {len(cached)} of {len(lines)} lines have audio; {spoken} synthesised just now")
    return cached


def voice_router(cache_dir: Path = CACHE_DIR) -> APIRouter:
    """GET /voice/<name>.wav: one cached line. Nothing else in the folder can be reached."""
    router = APIRouter()

    @router.get(URL_PREFIX + "/{name}")
    def line(name: str) -> FileResponse:
        path = cache_dir / name
        if not _NAME.fullmatch(name) or not path.is_file():
            raise HTTPException(status_code=404, detail="no such line")
        # The name is a hash of the words: the same name is always the same audio.
        return FileResponse(
            path, media_type="audio/wav", headers={"Cache-Control": "max-age=31536000"}
        )

    return router
