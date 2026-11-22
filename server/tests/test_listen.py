"""A spoken answer arriving as a clip: transcribed, then handed on like a typed one."""

import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tacto import listen, voice_models
from tacto.contract import AnswerReflection

WAV = b"RIFF" + b"\x00" * 200
AUDIO = {"content-type": "audio/wav"}


class Lab:
    """Stands in for the lab: remembers what it was handed."""

    def __init__(self) -> None:
        self.handled: list = []

    def handle(self, message) -> None:
        self.handled.append(message)


def client_for(lab: Lab, transcriber) -> TestClient:
    app = FastAPI()
    app.include_router(listen.answer_router(lab, transcriber))
    return TestClient(app)


def test_a_clip_is_transcribed_and_handed_to_the_lab_as_an_answer():
    lab, heard = Lab(), []

    def transcriber(wav: bytes) -> str:
        heard.append(wav)
        return "more push so more flow"

    response = client_for(lab, transcriber).post(
        "/voice/answer", params={"step_id": "raise_voltage"}, content=WAV, headers=AUDIO
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "more push so more flow" and body["transcribed"] is True
    assert body["transcribe_ms"] >= 0
    assert heard == [WAV]
    assert lab.handled == [AnswerReflection(step_id="raise_voltage", text="more push so more flow")]


@pytest.mark.parametrize("what", ["the service fails", "there is no transcriber"])
def test_a_clip_that_cannot_be_transcribed_is_an_empty_answer_not_an_error(what):
    def broken(wav: bytes) -> str:
        raise httpx.ConnectError("offline")

    lab = Lab()
    response = client_for(lab, broken if what == "the service fails" else None).post(
        "/voice/answer", params={"step_id": "series"}, content=WAV, headers=AUDIO
    )
    assert response.status_code == 200, what
    assert response.json()["text"] == "" and response.json()["transcribed"] is False
    # An empty answer is graded "unclear": the question is asked again.
    assert lab.handled == [AnswerReflection(step_id="series", text="")]


def test_something_that_is_not_a_wav_file_is_refused_and_nothing_is_heard():
    lab, heard = Lab(), []
    response = client_for(lab, heard.append).post(
        "/voice/answer", params={"step_id": "series"}, content=b"<html>", headers=AUDIO
    )
    assert response.status_code == 400 and heard == [] and lab.handled == []


def test_a_clip_that_is_too_long_is_refused():
    lab, heard = Lab(), []
    too_long = b"RIFF" + b"\x00" * listen.MAX_CLIP_BYTES
    response = client_for(lab, heard.append).post(
        "/voice/answer", params={"step_id": "series"}, content=too_long, headers=AUDIO
    )
    assert response.status_code == 413 and heard == [] and lab.handled == []


def test_the_step_must_be_named():
    assert client_for(Lab(), lambda wav: "x").post("/voice/answer", content=WAV).status_code == 422


def test_a_very_long_transcript_is_cut_to_what_an_answer_may_hold():
    lab = Lab()
    client_for(lab, lambda wav: "word " * 1000).post(
        "/voice/answer", params={"step_id": "series"}, content=WAV, headers=AUDIO
    )
    assert len(lab.handled[0].text) <= 2000


def test_the_transcription_request_names_the_model_english_and_the_lab_words():
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"text": "  Higher voltage, more current. "})

    client = httpx.Client(base_url=voice_models.BASE_URL, transport=httpx.MockTransport(handle))
    assert listen.transcribe(WAV, client) == "Higher voltage, more current."
    assert seen[0].url.path.endswith("/audio/transcriptions")
    body = seen[0].content
    assert voice_models.STT_MODEL.encode() in body and WAV in body
    assert b'name="language"' in body and b"en" in body
    # A hint of the words to expect, so "current" is not heard as "currant".
    assert b"voltage" in body and b"resistance" in body
    # The docs ask for the model field before the file.
    assert body.index(b'name="model"') < body.index(b'name="file"')


def test_a_transcription_reply_without_text_raises_for_the_caller_to_handle():
    client = httpx.Client(
        base_url=voice_models.BASE_URL,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"oops": 1})),
    )
    with pytest.raises(KeyError):
        listen.transcribe(WAV, client)
    assert json.dumps({"ok": True})  # nothing else to check: the router turns this into ""
