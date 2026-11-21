from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from tacto.contract import ClientMessage, State
from tacto.main import app


def test_health():
    assert TestClient(app).get("/health").json()["ok"] is True


def test_state_stream_and_wheel():
    with TestClient(app).websocket_connect("/ws") as ws:
        first = State.model_validate_json(ws.receive_text())
        assert first.circuit.status == "closed"
        ws.send_text('{"type": "wheel", "steps": 4}')
        for _ in range(10):
            later = State.model_validate_json(ws.receive_text())
            if later.circuit.source_voltage > first.circuit.source_voltage:
                break
        assert later.circuit.source_voltage == first.circuit.source_voltage + 2.0
        assert later.circuit.parts[1].brightness > first.circuit.parts[1].brightness


def test_client_messages_parse():
    adapter = TypeAdapter(ClientMessage)
    assert (
        adapter.validate_json('{"type":"answer","choice":"brighter","via":"voice"}').via == "voice"
    )
    assert adapter.validate_json('{"type":"calibrate_touch","corner":2}').corner == 2
