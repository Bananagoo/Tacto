"""The virtual mat drives the real product: its routes change what the session sees."""

import pytest
from fastapi.testclient import TestClient

from tacto.app import create_app
from tacto.contract import State
from tacto.platform import open_platform
from tacto_bench.mat_routes import mat_router
from tacto_bench.virtual_mat import VirtualMat


@pytest.fixture
def client() -> TestClient:
    platform = open_platform(database_url="sqlite://")
    mat = VirtualMat(platform.layout)
    app = create_app(
        lambda nickname: platform.new_session(nickname=nickname, source=mat, source_name="mock"),
        source="mock",
    )
    app.include_router(mat_router(mat))
    return TestClient(app)


def latest_state(ws, wanted) -> State:
    for _ in range(30):
        state = State.model_validate_json(ws.receive_text())
        if wanted(state):
            return state
    raise AssertionError("the state never changed as expected")


def test_the_mat_starts_as_the_kit_ships(client):
    body = client.get("/dev/mat").json()
    assert body["drawn"] == []
    assert body["slots"] == {"tile": "wire", "side": "empty"}
    assert body["fingertip"] is None
    assert body["layout"]["id"] == "circuits-101"


def test_drawing_the_gap_closes_the_circuit_the_learner_sees(client):
    with client.websocket_connect("/ws?learner=tester") as ws:
        assert latest_state(ws, lambda s: True).circuit.status == "open"
        assert client.post("/dev/mat/draw", json={"id": "gap", "drawn": True}).json()["drawn"] == [
            "gap"
        ]
        assert latest_state(ws, lambda s: s.circuit.status == "closed").circuit.topology == "single"
        client.post("/dev/mat/draw", json={"id": "gap", "drawn": False})
        latest_state(ws, lambda s: s.circuit.status == "open")


def test_a_tile_and_a_fingertip_reach_the_session(client):
    client.post("/dev/mat/draw", json={"id": "gap", "drawn": True})
    client.post("/dev/mat/slot", json={"id": "tile", "content": "bulb"})
    client.post("/dev/mat/finger", json={"fingertip": {"x": 1.5 / 8, "y": 0.0}})
    with client.websocket_connect("/ws?learner=tester") as ws:
        state = latest_state(ws, lambda s: s.probe.present)
        assert state.circuit.topology == "series"
        assert state.probe.pulse_hz == pytest.approx(1.5, abs=0.01)
    client.post("/dev/mat/finger", json={"fingertip": None})
    assert client.get("/dev/mat").json()["fingertip"] is None


def test_reset_puts_the_kit_back(client):
    client.post("/dev/mat/draw", json={"id": "gap", "drawn": True})
    client.post("/dev/mat/slot", json={"id": "side", "content": "bulb"})
    body = client.post("/dev/mat/reset").json()
    assert (body["drawn"], body["slots"]) == ([], {"tile": "wire", "side": "empty"})


def test_mistakes_get_a_clear_refusal(client):
    assert client.post("/dev/mat/draw", json={"id": "moat", "drawn": True}).status_code == 404
    assert client.post("/dev/mat/slot", json={"id": "attic", "content": "bulb"}).status_code == 404
    assert client.post("/dev/mat/slot", json={"id": "tile", "content": "switch"}).status_code == 422
