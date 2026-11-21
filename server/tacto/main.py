"""The lab server. Run with `make dev` (uvicorn tacto.main:app --port 8000).

TACTO_SOURCE picks where the mat comes from:
  camera  the LogiInsight camera looking at the printed mat (default)
  replay  frames recorded into server/fixtures/<mat id>/ (scripts/record_frames.py)

Both go through the same reader (`vision/source.py`). GET /debug/reader says what it
last saw and how many milliseconds each step takes.

TACTO_CAMERA_INDEX overrides the camera, which is otherwise found by name.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from tacto.app import create_lab_app
from tacto.lab import Lab
from tacto.lesson import LessonRunner, load_lesson
from tacto.mat import load_default_mat
from tacto.pieces import warm_up_solver
from tacto.vision import camera, hands
from tacto.vision.focus import FocusKeeper
from tacto.vision.frames import FolderFrames, FramesOnAClock
from tacto.vision.source import CameraMatSource

load_dotenv()

SOURCE = os.getenv("TACTO_SOURCE", "camera")
CAMERA_NAME = "LVNext"
REPO = Path(__file__).resolve().parents[2]
LESSON_FILE = REPO / "lessons" / "circuits-101.yaml"
FIXTURES = REPO / "server" / "fixtures"

mat = load_default_mat()
hub = camera.CameraHub()
camera_index: int | None = None


def _camera_index() -> int:
    chosen = os.getenv("TACTO_CAMERA_INDEX")
    if chosen is not None:
        return int(chosen)
    for found in camera.list_cameras():
        if CAMERA_NAME in found["name"]:
            return found["index"]
    raise SystemExit(
        f"main: no camera named {CAMERA_NAME!r} is plugged in. Plug it in, set "
        "TACTO_CAMERA_INDEX, or run `make mock` to replay the recorded sample."
    )


def _hand_tracker() -> hands.HandTracker | None:
    try:
        return hands.HandTracker()
    except hands.HandTrackingUnavailable as error:
        print(f"main: no hand tracking, so no touch and no holding under a hand: {error}")
        return None


if SOURCE == "camera":
    camera_index = _camera_index()
    try:
        frames = hub.acquire(camera_index)
    except camera.CameraUnavailable as error:
        raise SystemExit(f"main: {error}") from error
    focus: FocusKeeper | None = FocusKeeper()
elif SOURCE == "replay":
    folder = FIXTURES / mat.id
    if not folder.is_dir() or not any(folder.iterdir()):
        raise SystemExit(
            f"main: no recorded frames in {folder}. Record some with scripts/record_frames.py."
        )
    frames = FramesOnAClock(FolderFrames(folder))
    focus = None
else:
    raise SystemExit(f"main: TACTO_SOURCE={SOURCE!r} is not one of: camera, replay")

warm_up_solver()
source = CameraMatSource(mat, frames, hands=_hand_tracker(), focus=focus)
source.start()

lab = Lab(
    mat.grid,
    source,
    source_name=SOURCE,  # type: ignore[arg-type]
    lesson=LessonRunner(load_lesson(LESSON_FILE)),
)
app = create_lab_app(lab, source=SOURCE)


@app.get("/debug/reader")
def reader_report() -> dict:
    return source.report()


@app.on_event("shutdown")
def _close_camera() -> None:
    # The camera must not be left streaming: Logitech's docs warn it can overheat.
    source.stop()
    if camera_index is not None:
        hub.release(camera_index)
