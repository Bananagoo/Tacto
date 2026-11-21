"""A live look at the desk for the page's corner: GET /camera/preview, a small MJPEG stream.

It shows the learner what the camera sees. Frames go to the browser that asked, on this
machine, and are never stored, so "nothing is recorded" still holds. It reuses the worker the
vision source already has open (one camera, one reader) and never opens a camera of its own:
with no camera open (replay, or `make bench`) it answers 404 and the page shows nothing.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from . import camera

BOUNDARY = "frame"
FRAME_TIMEOUT_S = 1.0
# TODO(front end owner): tune on the projector. A corner picture does not need to be sharp or fast.
PREVIEW_WIDTH_PX = 480
MAX_PREVIEW_FPS = 10
JPEG_QUALITY = 70


def encode_jpeg(frame: np.ndarray, width_px: int = PREVIEW_WIDTH_PX) -> bytes:
    """JPEG bytes of `frame`, scaled down to `width_px` so the stream stays light."""
    if 0 < width_px < frame.shape[1]:
        height_px = round(frame.shape[0] * width_px / frame.shape[1])
        frame = cv2.resize(frame, (width_px, height_px), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise ValueError("could not encode frame")
    return encoded.tobytes()


def preview_router(hub: camera.CameraHub) -> APIRouter:
    """The preview route, reading from the same hub the vision source opened its camera on."""
    router = APIRouter(tags=["camera"])

    @router.get("/camera/preview")
    async def preview(
        frames: int | None = Query(None, ge=1, description="stop after this many frames"),
    ) -> StreamingResponse:
        open_cameras = hub.active()
        if not open_cameras:
            raise HTTPException(status_code=404, detail="no camera is open")
        index = open_cameras[0]
        try:
            worker = await asyncio.to_thread(hub.acquire, index)
        except camera.CameraUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        async def body() -> AsyncIterator[bytes]:
            try:
                seq = -1
                sent = 0
                last_sent = 0.0
                while frames is None or sent < frames:
                    got = await asyncio.to_thread(worker.wait_for_frame, seq, FRAME_TIMEOUT_S)
                    if got is None:
                        if worker.error is not None:
                            break
                        continue
                    seq, frame = got
                    if time.monotonic() - last_sent < 1 / MAX_PREVIEW_FPS:
                        continue
                    last_sent = time.monotonic()
                    jpeg = await asyncio.to_thread(encode_jpeg, frame)
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
                # Also runs when the browser closes the stream. The vision source keeps its
                # own hold on the camera, so releasing ours never turns it off under it.
                await asyncio.shield(asyncio.to_thread(hub.release, index))

        return StreamingResponse(
            body(),
            media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
            headers={"Cache-Control": "no-store"},
        )

    return router
