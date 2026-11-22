"""Check that the three Together calls the voice layer needs work on this account.

One round is: speak a sentence (text to speech), transcribe that audio back (speech to
text), and grade a sample answer into a fixed label (chat with a JSON schema). It prints
how long each took. Run it from server/ so uv uses the project environment:

    uv run python ../scripts/together_smoke.py            # three rounds
    uv run python ../scripts/together_smoke.py --rounds 1

It needs TOGETHER_API_KEY in the repo's .env and the network, and each round costs a
fraction of a cent. The models are the ones in server/tacto/voice_models.py. The key is
read from the environment and never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "server"))

from tacto import voice_models  # noqa: E402

SENTENCE = "Why did the pulse get faster when you raised the voltage?"
# Words the transcript must contain for the round trip to count.
EXPECTED_WORDS = ("pulse", "faster", "voltage")
QUESTION = "Does a higher voltage push more current round the loop, or less?"
ANSWER = "more push so more flow i think"
LABELS = ["correct", "partial", "incorrect", "unclear"]
SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": LABELS}},
    "required": ["label"],
    "additionalProperties": False,
}
TIMEOUT_S = 30.0


def speak(client: httpx.Client) -> bytes:
    response = client.post(
        "/audio/speech",
        json={
            "model": voice_models.TTS_MODEL,
            "input": SENTENCE,
            "voice": voice_models.TTS_VOICE,
            "response_format": "wav",
        },
    )
    response.raise_for_status()
    if not response.content.startswith(b"RIFF"):
        size = len(response.content)
        raise RuntimeError(f"text to speech did not return a WAV file ({size} bytes)")
    return response.content


def transcribe(client: httpx.Client, wav: bytes) -> str:
    response = client.post(
        "/audio/transcriptions",
        # The docs ask for the model field before the file.
        data={"model": voice_models.STT_MODEL, "language": "en", "response_format": "json"},
        files={"file": ("line.wav", wav, "audio/wav")},
    )
    response.raise_for_status()
    return str(response.json()["text"]).strip()


def grade(client: httpx.Client) -> str:
    response = client.post(
        "/chat/completions",
        json={
            "model": voice_models.GRADER_MODEL,
            "temperature": 0,
            "max_tokens": 50,
            "reasoning": {"enabled": False},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "grade", "schema": SCHEMA},
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You grade a student's spoken answer to a physics question. Reply only "
                        f"in JSON matching this schema: {json.dumps(SCHEMA)}. Grade the idea, "
                        "not the vocabulary."
                    ),
                },
                {"role": "user", "content": f"Question: {QUESTION}\nAnswer: {ANSWER}"},
            ],
        },
    )
    response.raise_for_status()
    choice = response.json()["choices"][0]
    if choice.get("finish_reason") == "length":
        raise RuntimeError("the grader's answer was cut off")
    label = json.loads(choice["message"]["content"])["label"]
    if label not in LABELS:
        raise RuntimeError(f"the grader returned a label outside the set: {label!r}")
    return label


def timed(call, *args):
    started = time.perf_counter()
    result = call(*args)
    return result, time.perf_counter() - started


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()

    load_dotenv(REPO / ".env")
    key = os.getenv("TOGETHER_API_KEY", "").strip()
    if not key:
        raise SystemExit("together_smoke: TOGETHER_API_KEY is not set in .env")
    print(
        f"models: speech {voice_models.TTS_MODEL} ({voice_models.TTS_VOICE}), "
        f"transcription {voice_models.STT_MODEL}, grader {voice_models.GRADER_MODEL}"
    )
    failed = 0
    with httpx.Client(
        base_url=voice_models.BASE_URL,
        headers={"Authorization": f"Bearer {key}", "User-Agent": "tacto-smoke/0.1"},
        timeout=TIMEOUT_S,
    ) as client:
        for number in range(1, args.rounds + 1):
            try:
                wav, speak_s = timed(speak, client)
                heard, hear_s = timed(transcribe, client, wav)
                label, grade_s = timed(grade, client)
            except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as error:
                failed += 1
                detail = getattr(getattr(error, "response", None), "text", "")[:300]
                print(f"round {number}: FAILED: {type(error).__name__}: {error} {detail}")
                continue
            missing = [word for word in EXPECTED_WORDS if word not in heard.lower()]
            ok = not missing
            failed += not ok
            print(
                f"round {number}: {'ok' if ok else 'MISHEARD'}  "
                f"speech {speak_s:.2f} s ({len(wav) // 1024} kB)  "
                f"transcription {hear_s:.2f} s  grader {grade_s:.2f} s -> {label}"
            )
            print(f"         heard: {heard!r}" + (f"  missing {missing}" if missing else ""))
    if failed:
        raise SystemExit(f"together_smoke: {failed} of {args.rounds} rounds failed")
    print(f"together_smoke: {args.rounds} of {args.rounds} rounds passed")


if __name__ == "__main__":
    main()
