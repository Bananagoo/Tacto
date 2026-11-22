"""The tooling server: the camera bench.

Run with `make bench` and open localhost:5173/devtools/. It shows what the camera sees,
the flattened mat and each segment's reading, and sets the camera's exposure. The lab
itself is `make dev`.
"""

from __future__ import annotations

from fastapi import FastAPI

from .camera_routes import router as camera_router

app = FastAPI(title="Tacto bench")
app.include_router(camera_router)
