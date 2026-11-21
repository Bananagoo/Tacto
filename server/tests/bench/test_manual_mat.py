import pytest
from fastapi.testclient import TestClient

from tacto.contract_v2 import Grid, State
from tacto.lab import Lab
from tacto.lab_app import create_lab_app
from tacto_bench.manual_mat import PRESETS, ManualMat
from tacto_bench.manual_routes import manual_router

GRID = Grid(cols=9, rows=6)


def types(mat: ManualMat) -> dict[str, str]:
    return {piece.id: piece.type for piece in mat.view().placed}


def test_a_tool_places_replaces_and_removes():
    mat = ManualMat(GRID)
    mat.use_tool("wire", (1, 1), (2, 1))
    assert types(mat) == {"1,1-2,1": "wire"}
    mat.use_tool("bulb", (2, 1), (1, 1))  # same segment, named from the other end
    assert types(mat) == {"1,1-2,1": "bulb"}
    mat.use_tool("bulb", (1, 1), (2, 1))
    assert types(mat) == {}
    mat.use_tool("wire", (1, 1), (2, 1))
    mat.use_tool("erase", (1, 1), (2, 1))
    mat.use_tool("erase", (1, 1), (2, 1))  # erasing nothing is fine
    assert types(mat) == {}


def test_the_switch_tool_toggles_a_switch():
    mat = ManualMat(GRID)
    mat.use_tool("switch", (4, 1), (4, 2))
    assert mat.view().placed[0].closed is False
    mat.use_tool("switch", (4, 1), (4, 2))
    assert mat.view().placed[0].closed is True


def test_the_battery_tool_turns_a_battery_round():
    mat = ManualMat(GRID)
    mat.use_tool("battery", (1, 1), (1, 2))
    assert mat.view().placed[0].a == (1, 1)
    mat.use_tool("battery", (1, 1), (1, 2))
    assert mat.view().placed[0].a == (1, 2)


@pytest.mark.parametrize(
    "a, b", [((1, 1), (3, 1)), ((1, 1), (2, 2)), ((8, 1), (9, 1)), ((0, 0), (0, -1))]
)
def test_bad_segments_are_refused(a, b):
    with pytest.raises(ValueError):
        ManualMat(GRID).use_tool("wire", a, b)


@pytest.mark.parametrize(
    "preset, status",
    [
        ("empty", "open"),
        ("open", "open"),
        ("one_bulb", "working"),
        ("series", "working"),
        ("parallel", "working"),
        ("short", "shorted"),
        ("resistor", "working"),
    ],
)
def test_every_preset_gives_its_state(preset, status):
    mat = ManualMat(GRID)
    mat.load_preset(preset)
    assert Lab(GRID, mat, source_name="manual").state().circuit.status == status
    assert set(PRESETS) == {"empty", "open", "one_bulb", "series", "parallel", "short", "resistor"}


def test_the_routes_drive_the_state_message():
    mat = ManualMat(GRID)
    lab = Lab(GRID, mat, source_name="manual")
    app = create_lab_app(lab, source="manual")
    app.include_router(manual_router(mat, lab))
    client = TestClient(app)

    assert "Hand-set mat" in client.get("/manual").text
    assert "short" in client.get("/manual/presets").json()
    assert client.post("/manual/preset", json={"name": "open"}).status_code == 200
    assert lab.state().circuit.status == "open"

    # Tap the switch closed, then rest a finger on bulb A.
    client.post("/manual/tool", json={"tool": "switch", "a": [4, 1], "b": [4, 2]})
    client.post("/manual/finger", json={"x": 2.5 / 8, "y": 1 / 5})
    state: State = lab.state()
    assert state.circuit.status == "working"
    assert state.touch.piece_id == "2,1-3,1" and state.touch.pulse_hz == pytest.approx(
        3.0, abs=0.01
    )

    client.post("/manual/finger", json={"present": False})
    client.post("/manual/mat_visible", json={"visible": False})
    state = lab.state()
    assert not state.touch.present and not state.mat_visible

    assert client.post("/manual/preset", json={"name": "nope"}).status_code == 404
    assert (
        client.post("/manual/tool", json={"tool": "wire", "a": [1, 1], "b": [3, 1]}).status_code
        == 422
    )
    assert (
        client.post("/manual/tool", json={"tool": "laser", "a": [1, 1], "b": [2, 1]}).status_code
        == 422
    )
