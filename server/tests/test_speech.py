"""The speech relay, against an in-memory stand-in for Together. No network, no inference."""

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tacto import speech

KEY = "test-key-never-sent-to-the-browser"
SAME_ORIGIN = {"origin": "http://testserver"}
HALF_SECOND = b"\x01\x00" * 8000  # 16 kHz, 16-bit


class FakeTogether:
    """What the relay talks to: says hello, then answers each commit with one transcript."""

    def __init__(self, transcripts=("hello there", "it got faster"), fail_on_commit=False) -> None:
        self._transcripts = list(transcripts)
        self._fail_on_commit = fail_on_commit
        self.sent: list[dict] = []
        self.opened_with: str | None = None

    async def __aenter__(self):
        self._events: asyncio.Queue = asyncio.Queue()
        await self._events.put({"type": "session.created"})
        return self

    async def __aexit__(self, *error) -> bool:
        return False

    async def recv(self) -> str:
        return json.dumps(await self._events.get())

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        return json.dumps(await self._events.get())

    async def send(self, raw: str) -> None:
        message = json.loads(raw)
        self.sent.append(message)
        if message["type"] != "input_audio_buffer.commit":
            return
        if self._fail_on_commit:
            await self._events.put(
                {"type": "error", "error": {"message": "upstream secret detail"}}
            )
            return
        text = self._transcripts.pop(0)
        kind = "conversation.item.input_audio_transcription"
        await self._events.put({"type": f"{kind}.delta", "delta": text[:4]})
        await self._events.put({"type": f"{kind}.completed", "transcript": text})


@pytest.fixture
def together(monkeypatch) -> FakeTogether:
    fake = FakeTogether()

    def connect(api_key: str) -> FakeTogether:
        fake.opened_with = api_key
        return fake

    monkeypatch.setenv("TOGETHER_API_KEY", KEY)
    monkeypatch.setattr(speech, "together_connection", connect)
    return fake


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(speech.speech_router())
    return TestClient(app)


def start(socket, step_id: str = "raise_voltage") -> dict:
    socket.send_text(json.dumps({"type": "start", "step_id": step_id}))
    return socket.receive_json()


def until(socket, kind: str) -> dict:
    """The next message of one kind; transcripts in between are passed over."""
    for _ in range(20):
        message = socket.receive_json()
        if message["type"] == kind:
            return message
    raise AssertionError(f"no {kind!r} message arrived")


def test_status_says_whether_a_key_is_set_and_never_what_it_is(client, monkeypatch):
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    assert client.get("/speech/status").json() == {"configured": False}
    monkeypatch.setenv("TOGETHER_API_KEY", KEY)
    assert client.get("/speech/status").json() == {"configured": True}


def test_another_website_cannot_use_the_relay(client, together):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect("/speech/ws", headers={"origin": "http://evil.example"}):
            pass
    assert closed.value.code == 1008
    assert together.opened_with is None


def test_without_a_key_it_says_so_and_opens_nothing(client, together, monkeypatch):
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        message = socket.receive_json()
    assert message["type"] == "error" and "TOGETHER_API_KEY" in message["message"]
    assert together.opened_with is None


def test_nothing_is_opened_upstream_until_the_learner_starts(client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        assert together.opened_with is None
        assert start(socket) == {"type": "ready", "step_id": "raise_voltage"}
        assert together.opened_with == KEY


def test_two_spoken_segments_come_back_as_one_answer(client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        start(socket)
        seen = []
        for _ in range(2):
            socket.send_bytes(HALF_SECOND)
            socket.send_text(json.dumps({"type": "commit"}))
            # A provisional phrase, then the finished one.
            seen.append(until(socket, "transcript"))
            seen.append(until(socket, "transcript"))
        socket.send_text(json.dumps({"type": "finish"}))
        answer = until(socket, "answer")
    assert answer == {
        "type": "answer",
        "step_id": "raise_voltage",
        "text": "hello there it got faster",
    }
    assert seen[0]["partial"] == "hell" and seen[1] == {
        "type": "transcript",
        "text": "hello there",
        "partial": "",
    }
    kinds = [message["type"] for message in together.sent]
    assert kinds == ["input_audio_buffer.append", "input_audio_buffer.commit"] * 2
    assert KEY not in json.dumps([answer, *seen])


def test_finishing_without_speaking_is_an_empty_answer_not_a_hang(client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        start(socket)
        socket.send_text(json.dumps({"type": "finish"}))
        assert until(socket, "answer")["text"] == ""
    assert together.sent == []


def test_a_commit_with_no_audio_is_not_sent_on(client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        start(socket)
        socket.send_text(json.dumps({"type": "commit"}))
        socket.send_text(json.dumps({"type": "finish"}))
        assert until(socket, "answer")["text"] == ""
    assert together.sent == []


@pytest.mark.parametrize(
    "audio", [b"\x01", b"\x01\x00\x01", b"\x00" * (speech.BYTES_PER_SECOND + 2)]
)
def test_audio_that_is_not_whole_samples_or_is_too_big_is_refused(audio, client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        start(socket)
        socket.send_bytes(audio)
        message = until(socket, "error")
    assert "Invalid microphone audio" in message["message"]
    assert together.sent == []


def test_an_unknown_control_is_refused(client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        start(socket)
        socket.send_text(json.dumps({"type": "delete_everything"}))
        assert until(socket, "error")["message"] == "Invalid speech control."


@pytest.mark.parametrize("step_id", ["", "has spaces", "../../etc", "x" * 101])
def test_a_bad_start_is_refused_before_anything_is_opened(step_id, client, together):
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        socket.send_text(json.dumps({"type": "start", "step_id": step_id}))
        assert socket.receive_json()["type"] == "error"
    assert together.opened_with is None


def test_the_providers_own_error_text_never_reaches_the_browser(client, monkeypatch):
    failing = FakeTogether(fail_on_commit=True)
    monkeypatch.setenv("TOGETHER_API_KEY", KEY)
    monkeypatch.setattr(speech, "together_connection", lambda api_key: failing)
    with client.websocket_connect("/speech/ws", headers=SAME_ORIGIN) as socket:
        start(socket)
        socket.send_bytes(HALF_SECOND)
        socket.send_text(json.dumps({"type": "commit"}))
        message = until(socket, "error")
    assert message["message"] == "Together could not transcribe this answer. Please try again."
    assert "secret" not in json.dumps(message)
