"""The app serves any World: it streams its state and forwards the learner's messages."""

from fastapi.testclient import TestClient

from tacto.app import create_app
from tacto.contract import ClientMessage, State, Wheel


class FakeWorld:
    def __init__(self) -> None:
        self.received: list[ClientMessage] = []

    def state(self) -> State:
        return State(t=float(len(self.received)))

    def handle(self, message: ClientMessage) -> None:
        self.received.append(message)


def test_health_names_the_source():
    app = create_app(FakeWorld, source="fake")
    assert TestClient(app).get("/health").json() == {"ok": True, "source": "fake"}


def test_socket_streams_state_and_forwards_messages():
    worlds: list[FakeWorld] = []

    def make_world() -> FakeWorld:
        worlds.append(FakeWorld())
        return worlds[-1]

    with TestClient(create_app(make_world, source="fake")).websocket_connect("/ws") as ws:
        assert State.model_validate_json(ws.receive_text()).t == 0.0
        ws.send_text('{"type": "wheel", "steps": 2}')
        for _ in range(10):
            if State.model_validate_json(ws.receive_text()).t == 1.0:
                break
        assert worlds[0].received == [Wheel(steps=2)]


def test_a_malformed_message_does_not_close_the_socket():
    world = FakeWorld()
    with TestClient(create_app(lambda: world, source="fake")).websocket_connect("/ws") as ws:
        ws.send_text("not json")
        ws.send_text('{"type": "next"}')
        for _ in range(10):
            if State.model_validate_json(ws.receive_text()).t == 1.0:
                break
        assert len(world.received) == 1
