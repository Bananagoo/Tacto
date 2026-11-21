"""Camera bench routes and overlays. No real camera is opened in these tests."""

import threading
import time

import cv2
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tacto.vision import camera, hands
from tacto_bench import camera_routes as routes
from tacto_bench import overlays

# The camera routes on their own app: importing tacto_bench.main would open the database.
app = FastAPI()
app.include_router(routes.router)


def sheet(ids=(0, 1, 2, 3)) -> np.ndarray:
    """A white 1280x720 frame with one marker near each corner, like the printed test sheet."""
    frame = np.full((720, 1280, 3), 255, dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    spots = {0: (40, 40), 1: (1120, 40), 2: (1120, 560), 3: (40, 560)}
    for marker_id in ids:
        x, y = spots[marker_id]
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 120)
        frame[y : y + 120, x : x + 120] = marker[:, :, None]
    return frame


class FakeCapture:
    def __init__(self, frame: np.ndarray) -> None:
        self.frame = frame
        self.released = False

    def read(self):
        time.sleep(0.005)
        return True, self.frame.copy()

    def release(self) -> None:
        self.released = True


def fake_hub(frame: np.ndarray, opened: list[FakeCapture]) -> camera.CameraHub:
    def open_capture(index: int):
        if index != 0:
            return None
        capture = FakeCapture(frame)
        opened.append(capture)
        return capture

    return camera.CameraHub(open_capture)


# ---------- overlays ----------


def test_all_four_corner_markers_are_found():
    _, analysis = overlays.analyse(sheet(), {"aruco"}, None, 0)
    assert analysis["marker_ids"] == [0, 1, 2, 3]
    assert analysis["corners_visible"] is True
    assert analysis["missing_corners"] == []


def test_a_hidden_corner_is_reported_missing():
    _, analysis = overlays.analyse(sheet(ids=(0, 1, 3)), {"aruco"}, None, 0)
    assert analysis["corners_visible"] is False
    assert analysis["missing_corners"] == [2]


def test_no_overlay_leaves_the_frame_untouched():
    frame = sheet()
    drawn, analysis = overlays.analyse(frame, set(), None, 0)
    assert np.array_equal(drawn, frame)
    assert "marker_ids" not in analysis
    assert analysis["width"] == 1280 and analysis["height"] == 720


def test_jpeg_is_scaled_to_the_requested_width():
    jpeg = overlays.encode_jpeg(sheet(), width=640)
    assert jpeg[:2] == b"\xff\xd8"
    decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (360, 640)


# ---------- camera hub ----------


def test_camera_is_shared_and_released_when_the_last_viewer_leaves():
    opened: list[FakeCapture] = []
    hub = fake_hub(sheet(), opened)

    first = hub.acquire(0)
    second = hub.acquire(0)
    assert first is second
    assert len(opened) == 1

    hub.release(0)
    assert opened[0].released is False
    assert hub.active() == [0]

    hub.release(0)
    assert opened[0].released is True
    assert hub.active() == []


def test_worker_hands_out_new_frames_and_measures_fps():
    hub = fake_hub(sheet(), [])
    worker = hub.acquire(0)
    try:
        got = worker.wait_for_frame(after=-1, timeout=1.0)
        assert got is not None
        seq, frame = got
        assert frame.shape == (720, 1280, 3)
        later = worker.wait_for_frame(after=seq, timeout=1.0)
        assert later is not None and later[0] > seq
        time.sleep(0.3)
        assert worker.fps > 10
    finally:
        hub.release(0)


def test_a_camera_that_will_not_open_raises():
    hub = fake_hub(sheet(), [])
    with pytest.raises(camera.CameraUnavailable):
        hub.acquire(5)
    assert hub.active() == []


def test_camera_names_follow_opencv_order():
    # OpenCV's AVFoundation backend orders devices by unique id, not in the order macOS lists them.
    listing = {
        "SPCameraDataType": [
            {"_name": "LVNext Camera", "spcamera_unique-id": "0x200000046d094f"},
            {"_name": "FaceTime HD Camera", "spcamera_unique-id": "47B4B64B"},
            {"_name": "Phone", "spcamera_unique-id": "1DB5EDC1"},
        ]
    }
    assert camera.parse_camera_listing(listing) == [
        {"index": 0, "name": "LVNext Camera"},
        {"index": 1, "name": "Phone"},
        {"index": 2, "name": "FaceTime HD Camera"},
    ]


# ---------- routes ----------


@pytest.fixture
def client(monkeypatch):
    opened: list[FakeCapture] = []
    monkeypatch.setattr(routes, "hub", fake_hub(sheet(), opened))
    monkeypatch.setattr(camera, "list_cameras", lambda: [{"index": 0, "name": "LVNext Camera"}])
    test_client = TestClient(app)
    test_client.opened = opened
    return test_client


def test_cameras_route_lists_devices(client):
    body = client.get("/dev/cameras").json()
    assert body == {"cameras": [{"index": 0, "name": "LVNext Camera"}], "open": []}


def test_status_of_a_closed_camera(client):
    assert client.get("/dev/camera/status", params={"index": 0}).json() == {"open": False}


def test_stream_sends_jpeg_frames_then_releases_the_camera(client):
    response = client.get(
        "/dev/camera/stream", params={"index": 0, "overlay": "aruco", "frames": 2}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert response.content.count(b"Content-Type: image/jpeg") == 2
    assert response.headers["x-tacto-camera"] == "0"
    # The stream ended, so nobody is watching and the camera must be closed again.
    deadline = time.time() + 2
    while not client.opened[0].released and time.time() < deadline:
        time.sleep(0.01)
    assert client.opened[0].released is True


def test_status_reports_what_the_stream_saw(client, monkeypatch):
    hub = routes.hub
    worker = hub.acquire(0)
    try:
        done = threading.Event()

        def watch():
            client.get("/dev/camera/stream", params={"index": 0, "overlay": "aruco", "frames": 2})
            done.set()

        threading.Thread(target=watch, daemon=True).start()
        assert done.wait(5)
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["open"] is True
        assert status["width"] == 1280 and status["height"] == 720
        assert status["corners_visible"] is True
        assert status["fps"] > 0
    finally:
        hub.release(0)
        assert worker is not None


def test_stream_of_a_missing_camera_is_a_503(client):
    response = client.get("/dev/camera/stream", params={"index": 5, "frames": 1})
    assert response.status_code == 503
    assert "camera 5" in response.json()["detail"]


def test_hand_overlay_without_mediapipe_reports_why(client, monkeypatch):
    def broken(*_args, **_kwargs):
        raise hands.HandTrackingUnavailable("mediapipe is not installed")

    monkeypatch.setattr(hands, "HandTracker", broken)
    hub = routes.hub
    hub.acquire(0)
    try:
        client.get("/dev/camera/stream", params={"index": 0, "overlay": "hand", "frames": 1})
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["hand_error"] == "mediapipe is not installed"
    finally:
        hub.release(0)


class FakeTracker:
    """Stands in for MediaPipe: one right hand with 21 points on a diagonal."""

    def hands(self, frame, t_ms):
        return [
            {"handedness": "Right", "points": [[100 + 20 * i, 200 + 10 * i] for i in range(21)]}
        ]


def test_hand_overlay_reports_and_draws_all_21_points():
    frame = sheet()
    drawn, analysis = overlays.analyse(frame, {"hand"}, FakeTracker(), 0)
    assert len(analysis["hands"]) == 1
    assert len(analysis["hands"][0]["points"]) == 21
    # Point 8 is the index fingertip; it stays available on its own for the readout.
    assert analysis["fingertips"] == [{"handedness": "Right", "x": 260, "y": 280}]
    assert not np.array_equal(drawn, frame)
    assert np.array_equal(frame, sheet()), "the camera's frame must not be drawn on"


def test_status_combines_what_every_viewer_saw(client):
    # Two tabs can watch one camera with different overlays; neither should blank the other.
    worker = routes.hub.acquire(0)
    try:
        worker.analyses[1] = {"width": 1280, "marker_ids": [0, 3]}
        worker.analyses[2] = {
            "width": 1280,
            "fingertips": [{"handedness": "Right", "x": 5, "y": 6}],
        }
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["marker_ids"] == [0, 3]
        assert status["fingertips"][0]["x"] == 5
    finally:
        routes.hub.release(0)


def test_mat_overlay_reports_the_reader_result_for_the_frame(client, monkeypatch):
    from tacto.mat.loader import load_mat
    from tacto.platform import MATS_DIR
    from tacto.vision.kit_render import render_mat

    layout = load_mat(MATS_DIR / "circuits-101.yaml")
    monkeypatch.setattr(routes, "hub", fake_hub(render_mat(layout), []))
    hub = routes.hub
    hub.acquire(0)
    try:
        client.get("/dev/camera/stream", params={"index": 0, "overlay": "mat", "frames": 1})
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["mat"] == {
            "found": True,
            "drawn": [],
            "slots": {"tile": "empty", "side": "empty"},
        }
    finally:
        hub.release(0)


def test_mat_overlay_says_when_the_mat_is_not_in_view(client, monkeypatch):
    # A bare desk. (The shared test frame has markers 0-3 in its corners, which is a mat.)
    desk = np.full((720, 1280, 3), 120, dtype=np.uint8)
    monkeypatch.setattr(routes, "hub", fake_hub(desk, []))
    hub = routes.hub
    hub.acquire(0)
    try:
        client.get("/dev/camera/stream", params={"index": 0, "overlay": "mat", "frames": 1})
        assert client.get("/dev/camera/status", params={"index": 0}).json()["mat"] == {
            "found": False
        }
    finally:
        hub.release(0)
