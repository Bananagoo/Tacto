"""Speaking the lab's lines from a cache: built once, never during a session."""

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tacto import tts, voice_models
from tacto.lesson import load_lesson

LESSON = load_lesson(Path(__file__).resolve().parents[2] / "lessons" / "circuits-101-full.yaml")
WAV = b"RIFF" + b"\x00" * 60


class Voice:
    """A stand-in for text to speech: counts what it is asked to say."""

    def __init__(self, *, fail_on: str | None = None, garbage: bool = False) -> None:
        self.said: list[str] = []
        self.fail_on, self.garbage = fail_on, garbage

    def __call__(self, text: str) -> bytes:
        self.said.append(text)
        if self.fail_on is not None and self.fail_on in text:
            raise httpx.ConnectError("offline")
        return b"<html>not audio</html>" if self.garbage else WAV + text.encode()


# ---------- which lines ----------


def test_every_line_the_lab_can_say_in_a_reflection_is_listed_once():
    lines = tts.lines_of(LESSON)
    # Three reflections: three questions, one confirmation and one exit line each.
    assert len(lines) == len(set(lines)) == 15
    assert "Why did the pulse get faster when you raised the voltage?" in lines
    assert "With two bulbs in a row, is the total resistance bigger or smaller?" in lines
    assert any(line.startswith("Yes. The battery feeds both branches") for line in lines)
    assert any("Touch the other bulb" in line for line in lines)
    # Step prompts are instructions on screen, not something the lab says aloud.
    assert not any("Swap in the closed switch" in line for line in lines)


def test_a_levels_own_confirmation_is_listed_too():
    from tacto.lesson import Lesson

    lesson = Lesson.model_validate(
        {
            "id": "x",
            "title": "X",
            "steps": [
                {
                    "id": "a",
                    "prompt": "p",
                    "done_when": {"status": "working"},
                    "reflection": {
                        "target_idea": "t",
                        "confirmation": "Yes.",
                        "levels": [
                            {"question": "Q0?", "correct_examples": ["a", "b"]},
                            {
                                "question": "Q1?",
                                "correct_examples": ["a", "b"],
                                "confirmation": "Exactly so.",
                            },
                        ],
                        "exit": {"line": "The idea.", "then": [{"touching": "bulb"}]},
                    },
                },
                {"id": "b", "prompt": "p", "done_when": {"status": "open"}, "reflection": "Plain?"},
            ],
        }
    )
    assert tts.lines_of(lesson) == ["Q0?", "Q1?", "Yes.", "Exactly so.", "The idea."]


# ---------- the cache ----------


def test_the_first_start_speaks_every_line_and_the_second_speaks_none(tmp_path):
    lines = tts.lines_of(LESSON)
    first = Voice()
    cached = tts.ensure_cached(lines, tmp_path, first)
    assert sorted(first.said) == sorted(lines) and set(cached) == set(lines)
    for line, name in cached.items():
        assert (tmp_path / name).read_bytes() == WAV + line.encode()

    second = Voice()
    again = tts.ensure_cached(lines, tmp_path, second)
    assert second.said == [] and again == cached


def test_with_the_network_down_cached_lines_are_still_found(tmp_path):
    lines = tts.lines_of(LESSON)
    cached = tts.ensure_cached(lines, tmp_path, Voice())
    assert tts.ensure_cached(lines, tmp_path, None) == cached


def test_only_a_new_or_reworded_line_is_spoken(tmp_path):
    tts.ensure_cached(["One.", "Two."], tmp_path, Voice())
    voice = Voice()
    cached = tts.ensure_cached(["One.", "Two, reworded.", "Three."], tmp_path, voice)
    assert voice.said == ["Two, reworded.", "Three."] and len(cached) == 3


def test_a_different_voice_or_model_is_a_different_file(monkeypatch):
    name = tts.file_name("Hello.")
    monkeypatch.setattr(voice_models, "TTS_VOICE", "another_voice")
    other_voice = tts.file_name("Hello.")
    monkeypatch.setattr(voice_models, "TTS_MODEL", "another/model")
    assert len({name, other_voice, tts.file_name("Hello.")}) == 3
    assert name.endswith(".wav") and "/" not in name and "Hello" not in name


def test_a_line_that_cannot_be_spoken_is_left_out_and_the_rest_are_kept(tmp_path):
    cached = tts.ensure_cached(["One.", "Two.", "Three."], tmp_path, Voice(fail_on="Two"))
    assert set(cached) == {"One.", "Three."}
    assert len(list(tmp_path.iterdir())) == 2


def test_a_reply_that_is_not_audio_is_not_cached(tmp_path):
    assert tts.ensure_cached(["One."], tmp_path, Voice(garbage=True)) == {}
    assert list(tmp_path.iterdir()) == []


def test_with_no_way_to_speak_and_nothing_cached_there_is_no_audio(tmp_path):
    assert tts.ensure_cached(["One."], tmp_path / "missing", None) == {}


# ---------- asking Together ----------


def test_the_request_names_the_model_the_voice_and_wav():
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=WAV)

    client = httpx.Client(base_url=voice_models.BASE_URL, transport=httpx.MockTransport(handle))
    assert tts.synthesise("Say this.", client) == WAV
    import json

    body = json.loads(seen[0].content)
    assert seen[0].url.path.endswith("/audio/speech")
    assert body == {
        "model": voice_models.TTS_MODEL,
        "input": "Say this.",
        "voice": voice_models.TTS_VOICE,
        "response_format": "wav",
    }


# ---------- serving ----------


@pytest.fixture
def served(tmp_path) -> tuple[TestClient, dict[str, str]]:
    cached = tts.ensure_cached(["One.", "Two."], tmp_path, Voice())
    app = FastAPI()
    app.include_router(tts.voice_router(tmp_path))
    return TestClient(app), cached


def test_a_cached_line_is_served_as_audio(served):
    client, cached = served
    response = client.get(tts.url_for(cached["One."]))
    assert response.status_code == 200 and response.headers["content-type"] == "audio/wav"
    assert response.content == WAV + b"One."


@pytest.mark.parametrize(
    "path",
    ["/voice/nope.wav", "/voice/..%2Fsecrets.wav", "/voice/abc.txt", "/voice/%2Fetc%2Fpasswd"],
)
def test_nothing_but_cached_lines_can_be_fetched(path, served):
    client, _ = served
    assert client.get(path).status_code == 404
