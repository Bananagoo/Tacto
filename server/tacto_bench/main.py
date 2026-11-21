"""The tooling server: the real product, fed by a virtual mat, plus the camera bench.

Run with `make bench` (uvicorn tacto_bench.main:app --reload --port 8000). Everything
behind the mat is the product's own code: the solver, the lesson engine, the database.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from tacto.app import create_app
from tacto.platform import open_platform
from tacto.store.db import DEFAULT_DATABASE_URL
from tacto.world import World

from .camera_routes import router as camera_router
from .mat_routes import mat_router
from .virtual_mat import VirtualMat

load_dotenv()

platform = open_platform(database_url=os.getenv("TACTO_DATABASE_URL", DEFAULT_DATABASE_URL))
virtual_mat = VirtualMat(platform.layout)


def make_world(nickname: str) -> World:
    return platform.new_session(nickname=nickname, source=virtual_mat, source_name="mock")


app = create_app(make_world, source="mock")
app.include_router(camera_router)
app.include_router(mat_router(virtual_mat))
