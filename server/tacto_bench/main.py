"""The tooling server: the product app, fed by the mock world, plus the camera bench.

Run with `make bench` (uvicorn tacto_bench.main:app --reload --port 8000).
"""

from __future__ import annotations

from tacto.app import create_app

from .camera_routes import router as camera_router
from .mock_world import MockWorld

app = create_app(MockWorld, source="mock")
app.include_router(camera_router)
