"""Camera bench routes and overlays. No real camera is opened in these tests."""

import threading
import time

import cv2
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tacto.vision import camera, exposure, hands
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


# ---------- exposure ----------


def test_exposure_routes_set_and_report_the_camera(client, monkeypatch):
    camera_now: dict[str, int | str] = {"auto-exposure-mode": 8, "gain": 0, "auto-focus": "true"}

    def tool(args: list[str]) -> tuple[int, str]:
        lines = []
        for flag, value in zip(args[::2], args[1::2], strict=True):
            if flag == "-s":
                name, new = value.split("=")
                camera_now[name] = new if name == "auto-focus" else int(new)
            elif flag == "-g":
                lines.append(f"{value} = {camera_now[value]}")
        return 0, "\n".join(lines)

    monkeypatch.setattr(exposure, "_run_tool", tool)
    monkeypatch.setattr(exposure, "_wanted", exposure.Exposure())
    monkeypatch.setattr(exposure, "available", lambda: True)

    before = client.get("/dev/camera/exposure").json()
    assert before == {
        "available": True,
        "camera_found": True,
        "manual": False,
        "gain": 0,
        "autofocus": True,
    }

    setting = {"manual": True, "gain": 25, "autofocus": False}
    after = client.post("/dev/camera/exposure", json=setting).json()
    assert after == {"available": True, "camera_found": True, **setting}
    assert camera_now["auto-focus"] == "false"
    assert camera_now["auto-exposure-mode"] == exposure.MANUAL_MODE
    assert exposure.wanted() == exposure.Exposure(manual=True, gain=25, autofocus=False)

    assert (
        client.post("/dev/camera/exposure", json={"manual": True, "gain": 300}).status_code == 422
    )


def test_exposure_route_without_the_tool_says_so(client, monkeypatch, tmp_path):
    monkeypatch.setattr(exposure, "TOOL", tmp_path / "uvc-util")
    monkeypatch.setattr(exposure, "_wanted", exposure.Exposure())
    body = client.get("/dev/camera/exposure").json()
    assert body["available"] is False and body["camera_found"] is False


# ---------- the flattened mat ----------


def last_jpeg(multipart: bytes) -> np.ndarray:
    start, end = multipart.rfind(b"\xff\xd8"), multipart.rfind(b"\xff\xd9")
    return cv2.imdecode(np.frombuffer(multipart[start : end + 2], np.uint8), cv2.IMREAD_COLOR)


def test_sharpness_falls_when_the_picture_is_blurred():
    crisp = sheet()
    soft = cv2.GaussianBlur(crisp, (0, 0), 6)
    assert overlays.sharpness(crisp) > 10 * overlays.sharpness(soft)


def test_flat_stream_shows_the_page_square_on_and_reports_the_mat(monkeypatch):
    from tacto.mat import load_default_mat
    from tacto.vision.kit_render import render_mat

    # The rendered mat page lying on a grey desk, off-centre in a 1080p frame.
    page = render_mat(load_default_mat(), dpi=100)
    frame = np.full((1080, 1920, 3), 90, dtype=np.uint8)
    frame[150 : 150 + page.shape[0], 400 : 400 + page.shape[1]] = page
    hub = fake_hub(frame, [])
    monkeypatch.setattr(routes, "hub", hub)
    client = TestClient(app)
    hub.acquire(0)  # keep the camera open so status can be read after the stream ends
    try:
        params = {"index": 0, "frames": 1, "flat": 1, "width": 1920}
        page = last_jpeg(client.get("/dev/camera/stream", params=params).content)
        # A4 landscape, and white paper right to the edge: no desk in the picture.
        assert abs(page.shape[1] / page.shape[0] - 297 / 210) < 0.01
        assert page[:, :8].mean() > 200 and page[:, -8:].mean() > 200
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["mat_found"] is True and status["mat_held"] is False
        assert status["corners_seen"] == [0, 1, 2, 3]
        assert status["sharpness"] > 0
    finally:
        hub.release(0)


def test_flat_stream_without_a_mat_shows_the_camera_and_says_so(monkeypatch):
    blank = np.full((720, 1280, 3), 90, dtype=np.uint8)
    hub = fake_hub(blank, [])
    monkeypatch.setattr(routes, "hub", hub)
    client = TestClient(app)
    hub.acquire(0)
    try:
        params = {"index": 0, "frames": 1, "flat": 1, "width": 1280}
        shown = last_jpeg(client.get("/dev/camera/stream", params=params).content)
        assert shown.shape[:2] == (720, 1280)
        status = client.get("/dev/camera/status", params={"index": 0}).json()
        assert status["mat_found"] is False and status["corners_seen"] == []
    finally:
        hub.release(0)
