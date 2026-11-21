"""Shared access to a camera: one reader thread per device, closed when nobody is watching.

The LogiInsight docs warn that the camera can overheat, so nothing here keeps a
device open on its own. A caller acquires a camera, reads frames, and releases it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Protocol

import cv2
import numpy as np

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FPS_WINDOW_S = 2.0
MAX_FAILED_READS = 100


class Capture(Protocol):
    def read(self) -> tuple[bool, np.ndarray | None]: ...
    def release(self) -> None: ...


class CameraUnavailable(RuntimeError):
    pass


def open_camera(index: int) -> Capture | None:
    backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
    capture = cv2.VideoCapture(index, backend)
    if not capture.isOpened():
        capture.release()
        return None
    # Size before format: the LogiInsight docs say the order matters.
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return capture


def parse_camera_listing(listing: dict) -> list[dict]:
    """Turn `system_profiler SPCameraDataType -json` into [{index, name}].

    OpenCV's AVFoundation backend orders devices by unique id, which is not the
    order macOS lists them in. Checked on this laptop on 21 Nov 2026.
    """
    devices = sorted(
        listing.get("SPCameraDataType", []), key=lambda d: d.get("spcamera_unique-id", "")
    )
    return [{"index": i, "name": d.get("_name", f"camera {i}")} for i, d in enumerate(devices)]


def list_cameras() -> list[dict]:
    """Camera names by OpenCV index. Empty when the names cannot be read (not macOS)."""
    if sys.platform != "darwin":
        return []
    try:
        output = subprocess.run(
            ["system_profiler", "SPCameraDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
        return parse_camera_listing(json.loads(output))
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"vision.camera: could not list cameras: {error}")
        return []


class CameraWorker:
    """Reads one camera on its own thread and keeps the latest frame."""

    def __init__(self, index: int, capture: Capture) -> None:
        self.index = index
        self.error: str | None = None
        self.analysis: dict = {}  # filled in by whoever is looking at the frames
        self._capture = capture
        self._condition = threading.Condition()
        self._frame: np.ndarray | None = None
        self._seq = -1
        self._times: deque[float] = deque()
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name=f"camera-{index}", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        failed = 0
        try:
            while not self._stopping:
                ok, frame = self._capture.read()
                if not ok or frame is None:
                    failed += 1
                    if failed > MAX_FAILED_READS:
                        self.error = "camera stopped sending frames"
                        break
                    time.sleep(0.01)
                    continue
                failed = 0
                now = time.monotonic()
                with self._condition:
                    self._frame = frame
                    self._seq += 1
                    self._times.append(now)
                    while self._times and now - self._times[0] > FPS_WINDOW_S:
                        self._times.popleft()
                    self._condition.notify_all()
        finally:
            self._capture.release()
            with self._condition:
                self._condition.notify_all()

    @property
    def fps(self) -> float:
        with self._condition:
            if len(self._times) < 2:
                return 0.0
            span = self._times[-1] - self._times[0]
            return round((len(self._times) - 1) / span, 1) if span > 0 else 0.0

    def wait_for_frame(self, after: int, timeout: float) -> tuple[int, np.ndarray] | None:
        """Block until a frame newer than `after` arrives. None on timeout or camera error."""
        with self._condition:
            self._condition.wait_for(
                lambda: self._seq > after or self.error is not None or self._stopping, timeout
            )
            if self._seq > after and self._frame is not None:
                return self._seq, self._frame
            return None

    def stop(self) -> None:
        self._stopping = True
        self._thread.join(timeout=3)


class CameraHub:
    """Hands out one shared worker per camera index and closes it after the last release."""

    def __init__(self, open_capture: Callable[[int], Capture | None] = open_camera) -> None:
        self._open = open_capture
        self._lock = threading.Lock()
        self._workers: dict[int, CameraWorker] = {}
        self._viewers: dict[int, int] = {}

    def acquire(self, index: int) -> CameraWorker:
        with self._lock:
            worker = self._workers.get(index)
            if worker is None or worker.error is not None:
                if worker is not None:
                    worker.stop()
                capture = self._open(index)
                if capture is None:
                    self._workers.pop(index, None)
                    self._viewers.pop(index, None)
                    raise CameraUnavailable(
                        f"camera {index} could not be opened; check it is plugged in and that "
                        "this terminal has Camera permission"
                    )
                worker = CameraWorker(index, capture)
                self._workers[index] = worker
                self._viewers[index] = 0
            self._viewers[index] += 1
            return worker

    def release(self, index: int) -> None:
        with self._lock:
            if index not in self._viewers:
                return
            self._viewers[index] -= 1
            if self._viewers[index] > 0:
                return
            worker = self._workers.pop(index)
            del self._viewers[index]
        worker.stop()

    def get(self, index: int) -> CameraWorker | None:
        with self._lock:
            return self._workers.get(index)

    def active(self) -> list[int]:
        with self._lock:
            return sorted(self._workers)
