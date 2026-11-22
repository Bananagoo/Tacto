"""The corner preview: it shares the vision source's camera and never opens one of its own.
No real camera is opened in these tests."""

import time

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tacto.vision import camera
from tacto.vision.preview import encode_jpeg, preview_router


class FakeCapture:
    def __init__(self) -> None:
        self.released = False

    def read(self):
        time.sleep(0.005)
        return True, np.full((720, 1280, 3), 200, dtype=np.uint8)

    def release(self) -> None:
        self.released = True


def client_for(hub: camera.CameraHub) -> TestClient:
    app = FastAPI()
    app.include_router(preview_router(hub))
    return TestClient(app)


def test_with_no_camera_open_the_preview_is_not_found():
    hub = camera.CameraHub(open_capture=lambda index: FakeCapture())
    response = client_for(hub).get("/camera/preview")
    assert response.status_code == 404
    assert hub.active() == []  # asking for a preview must not turn a camera on


def test_the_preview_streams_small_jpegs_and_leaves_the_camera_open():
    hub = camera.CameraHub(open_capture=lambda index: FakeCapture())
    hub.acquire(1)  # what the vision source holds
    response = client_for(hub).get("/camera/preview", params={"frames": 2})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert response.content.count(b"Content-Type: image/jpeg") == 2
    assert hub.active() == [1]  # the source still holds it after the viewer left
    hub.release(1)
    assert hub.active() == []


def test_frames_are_scaled_down_to_the_preview_width():
    import cv2

    jpeg = encode_jpeg(np.full((720, 1280, 3), 200, dtype=np.uint8), 480)
    decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (270, 480)
