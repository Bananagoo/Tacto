"""Open the source the product looks at the desk through: recorded frames or the camera."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from ..mat.models import MatLayout
from ..observation import Source
from . import camera, hands
from .live import CameraFrames, TrackedIndexFinger
from .source import FingerFinder, FolderFrames, VisionSource

SourceKind = Literal["replay", "camera"]
SOURCE_KINDS: tuple[SourceKind, ...] = ("replay", "camera")

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
# The camera is found by name, never by a fixed index: indices move when a phone
# or another webcam is connected.
CAMERA_NAME = "LVNext"


class SourceUnavailable(RuntimeError):
    pass


def open_source(
    kind: str,
    layout: MatLayout,
    *,
    fixtures_dir: Path = FIXTURES_DIR,
    hub: camera.CameraHub | None = None,
) -> Source:
    """A source for `kind`. Raises SourceUnavailable with what to do about it."""
    if kind == "replay":
        return _open_replay(layout, fixtures_dir / layout.id)
    if kind == "camera":
        return _open_camera(layout, hub or camera.CameraHub())
    raise SourceUnavailable(f"unknown TACTO_SOURCE {kind!r}; use one of {SOURCE_KINDS}")


def _open_replay(layout: MatLayout, frames_dir: Path) -> Source:
    if not frames_dir.is_dir():
        raise SourceUnavailable(
            f"no recorded frames in {frames_dir}; record some with "
            "scripts/record_frames.py, or run `make bench` for the virtual mat"
        )
    # No fingertip in replay: the hand tracker's model is a download, and recorded
    # frames must play back on any laptop.
    return VisionSource(layout, FolderFrames(frames_dir))


def _open_camera(layout: MatLayout, hub: camera.CameraHub) -> Source:
    index = _camera_index()
    try:
        worker = hub.acquire(index)
    except camera.CameraUnavailable as error:
        raise SourceUnavailable(str(error)) from error
    source = VisionSource(layout, CameraFrames(worker), _finger_finder())
    # On its own thread, so the server's event loop never waits on OpenCV.
    source.start()
    return source


def _camera_index() -> int:
    chosen = os.getenv("TACTO_CAMERA_INDEX")
    if chosen is not None:
        return int(chosen)
    for found in camera.list_cameras():
        if CAMERA_NAME in found["name"]:
            return found["index"]
    raise SourceUnavailable(
        f"no camera named {CAMERA_NAME!r} is connected; plug it in, or set TACTO_CAMERA_INDEX"
    )


def _finger_finder() -> FingerFinder | None:
    try:
        return TrackedIndexFinger(hands.HandTracker())
    except hands.HandTrackingUnavailable as error:
        # The mat still reads without it; only the fingertip is missing.
        print(f"vision.open: no fingertip tracking: {error}")
        return None
