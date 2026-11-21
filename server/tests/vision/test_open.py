"""Opening the product's source: recorded frames or the camera, found by name."""

import cv2
import numpy as np
import pytest

from tacto.mat.loader import load_mat
from tacto.platform import MATS_DIR
from tacto.vision import camera, hands
from tacto.vision import open as vision_open
from tacto.vision.kit_render import render_mat


@pytest.fixture(scope="module")
def layout():
    return load_mat(MATS_DIR / "circuits-101.yaml")


def test_replay_reads_the_recorded_frames_for_the_mat(layout, tmp_path):
    frames = tmp_path / layout.id
    frames.mkdir()
    cv2.imwrite(str(frames / "000.png"), render_mat(layout))
    source = vision_open.open_source("replay", layout, fixtures_dir=tmp_path)
    for _ in range(4):
        observation = source.observe()
    # The bare printed mat: nothing drawn, and no tile on either slot.
    assert observation.reading.drawn == frozenset()
    assert observation.reading.slots == {"tile": "empty", "side": "empty"}
    assert observation.fingertip is None


def test_replay_without_recordings_says_what_to_do(layout, tmp_path):
    with pytest.raises(vision_open.SourceUnavailable, match="record_frames.py"):
        vision_open.open_source("replay", layout, fixtures_dir=tmp_path)


def test_an_unknown_source_is_refused(layout):
    with pytest.raises(vision_open.SourceUnavailable, match="replay"):
        vision_open.open_source("telepathy", layout)


class FakeCapture:
    def __init__(self, frame: np.ndarray) -> None:
        self.frame = frame

    def read(self):
        return True, self.frame

    def release(self) -> None:
        pass


def no_hand_tracker():
    raise hands.HandTrackingUnavailable("no model in tests")


def test_the_camera_is_found_by_name_and_read_in_the_background(layout, monkeypatch):
    monkeypatch.delenv("TACTO_CAMERA_INDEX", raising=False)
    monkeypatch.setattr(
        camera,
        "list_cameras",
        lambda: [{"index": 0, "name": "Phone"}, {"index": 1, "name": "LVNext Camera"}],
    )
    monkeypatch.setattr(hands, "HandTracker", no_hand_tracker)
    opened: list[int] = []

    def open_capture(index: int):
        opened.append(index)
        return FakeCapture(render_mat(layout))

    hub = camera.CameraHub(open_capture)
    source = vision_open.open_source("camera", layout, hub=hub)
    try:
        assert opened == [1]
        assert source.observe().reading.drawn == frozenset()
    finally:
        source.stop()
        hub.release(1)


def test_a_missing_camera_says_what_to_do(layout, monkeypatch):
    monkeypatch.delenv("TACTO_CAMERA_INDEX", raising=False)
    monkeypatch.setattr(camera, "list_cameras", lambda: [{"index": 0, "name": "FaceTime"}])
    with pytest.raises(vision_open.SourceUnavailable, match="LVNext"):
        vision_open.open_source("camera", layout)


def test_the_camera_index_can_be_forced(layout, monkeypatch):
    monkeypatch.setenv("TACTO_CAMERA_INDEX", "3")
    monkeypatch.setattr(hands, "HandTracker", no_hand_tracker)
    hub = camera.CameraHub(lambda index: None)
    with pytest.raises(vision_open.SourceUnavailable, match="camera 3"):
        vision_open.open_source("camera", layout, hub=hub)
