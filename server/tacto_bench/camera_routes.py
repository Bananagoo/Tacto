"""Routes for the camera bench (web page at /devtools/#camera). Not part of the product.

GET /dev/cameras         camera names by index, and which are open
GET /dev/camera/stream   live MJPEG; overlay=aruco,hand draws or reports what was found;
                         flat=1 shows the mat squared up, as the reader sees it
GET /dev/camera/status   what the stream last saw: fps, size, markers, fingertips
GET /dev/camera/exposure   how the LogiInsight camera is exposing: manual or auto, and gain
POST /dev/camera/exposure  set it; it is applied again each time the camera is opened

A camera is open only while someone is watching its stream.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from tacto.mat import load_default_mat
from tacto.vision import camera, exposure, hands
from tacto.vision.print_geometry import PrintGeometry
from tacto.vision.tracker import MatTracker

from . import overlays

router = APIRouter(prefix="/dev", tags=["devtools"])
hub = camera.CameraHub()

BOUNDARY = "frame"
FRAME_TIMEOUT_S = 1.0
_viewer_ids = itertools.count(1)


@router.get("/cameras")
async def cameras() -> dict:
    return {"cameras": await asyncio.to_thread(camera.list_cameras), "open": hub.active()}


@router.get("/camera/status")
def status(index: int = 0) -> dict:
    worker = hub.get(index)
    if worker is None:
        return {"open": False}
    seen: dict = {}
    for analysis in list(worker.analyses.values()):
        seen.update(analysis)
    return {"open": True, "fps": worker.fps, "error": worker.error, **seen}


def _exposure_report() -> dict:
    now = exposure.read()
    return {
        "available": exposure.available(),
        "camera_found": now is not None,
        **(now or exposure.wanted()).model_dump(),
    }


@router.get("/camera/exposure")
def get_exposure() -> dict:
    return _exposure_report()


@router.post("/camera/exposure")
def set_exposure(setting: exposure.Exposure) -> dict:
    exposure.apply(setting)
    return _exposure_report()


@router.get("/camera/stream")
async def stream(
    index: int = 0,
    overlay: str = "",
    width: int = Query(1280, ge=160, le=1920),
    flat: bool = Query(False, description="send the flattened mat instead of the frame"),
    frames: int | None = Query(None, ge=1, description="stop after this many frames"),
) -> StreamingResponse:
    wanted = {name for name in overlay.split(",") if name}
    try:
        worker = await asyncio.to_thread(hub.acquire, index)
    except camera.CameraUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    async def body() -> AsyncIterator[bytes]:
        tracker = None
        hand_error = None
        viewer = next(_viewer_ids)
        mat_tracker = MatTracker(PrintGeometry.for_mat(load_default_mat())) if flat else None
        try:
            if "hand" in wanted:
                try:
                    tracker = await asyncio.to_thread(hands.HandTracker)
                except hands.HandTrackingUnavailable as error:
                    hand_error = str(error)
            seq = -1
            sent = 0
            start = time.monotonic()
            while frames is None or sent < frames:
                got = await asyncio.to_thread(worker.wait_for_frame, seq, FRAME_TIMEOUT_S)
                if got is None:
                    if worker.error is not None:
                        break
                    continue
                seq, frame = got
                t_ms = int((time.monotonic() - start) * 1000)
                drawn, analysis = await asyncio.to_thread(
                    overlays.analyse, frame, wanted, tracker, t_ms
                )
                if mat_tracker is not None:
                    page, report = await asyncio.to_thread(overlays.flat_view, frame, mat_tracker)
                    analysis.update(report)
                    # While the mat is not found, show the camera so it can be put right.
                    drawn = drawn if page is None else page
                if hand_error is not None:
                    analysis["hand_error"] = hand_error
                worker.analyses[viewer] = analysis
                jpeg = await asyncio.to_thread(overlays.encode_jpeg, drawn, width)
                yield (
                    (
                        f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpeg)}\r\n\r\n"
                    ).encode()
                    + jpeg
                    + b"\r\n"
                )
                sent += 1
        finally:
            # Runs when the browser closes the stream too, so the camera never stays on.
            # Keep the last viewer's reading so a status check just after still has it.
            if len(worker.analyses) > 1:
                worker.analyses.pop(viewer, None)
            await asyncio.shield(asyncio.to_thread(hub.release, index))
            if tracker is not None:
                tracker.close()

    return StreamingResponse(
        body(),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers={"Cache-Control": "no-store", "X-Tacto-Camera": str(index)},
    )
