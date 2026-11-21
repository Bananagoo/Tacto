"""Routes for the camera bench (web page at /devtools/#camera). Not part of the product.

GET /dev/cameras         camera names by index, and which are open
GET /dev/camera/stream   live MJPEG; overlay=aruco,hand draws what was found
GET /dev/camera/status   what the stream last saw: fps, size, markers, fingertips

A camera is open only while someone is watching its stream.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from tacto.vision import camera, hands

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


@router.get("/camera/stream")
async def stream(
    index: int = 0,
    overlay: str = "",
    width: int = Query(1280, ge=160, le=1920),
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
