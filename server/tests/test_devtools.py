"""Hardware test bench, server side. No real camera is opened in these tests."""

import threading
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from tacto import devtools as routes
from tacto.main import app
from tacto.vision import bench as overlays
from tacto.vision import camera


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
        raise overlays.HandTrackingUnavailable("mediapipe is not installed")

    monkeypatch.setattr(overlays, "HandTracker", broken)
    hub = routes.hub
    hub.acquire(0)
    try:
        client.get("/dev/camera/stream", params={"index": 0, "overlay": "hand", "frames": 1})
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["hand_error"] == "mediapipe is not installed"
    finally:
        hub.release(0)
