"""The mock world drives the product app the way the real session will."""

from fastapi.testclient import TestClient

from tacto.contract import State
from tacto_bench.main import app


def test_health_reports_the_mock_source():
    assert TestClient(app).get("/health").json() == {"ok": True, "source": "mock"}


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
