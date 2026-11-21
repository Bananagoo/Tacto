"""Tacto server. Run with `make dev` (uvicorn tacto.main:app --reload --port 8000).

TACTO_SOURCE picks where the world comes from:
  camera  the LogiInsight camera above the printed mat (default)
  replay  recorded frames from server/fixtures/<mat id>/

With no camera and no recordings, use `make bench`: the same product on a virtual mat.
"""

from __future__ import annotations

import os
import threading

from dotenv import load_dotenv

from .app import create_app
from .observation import Source
from .platform import Platform, open_platform
from .store.db import DEFAULT_DATABASE_URL
from .vision import camera
from .vision.open import open_source
from .vision.preview import preview_router
from .world import World

load_dotenv()

SOURCE = os.getenv("TACTO_SOURCE", "camera")
DATABASE_URL = os.getenv("TACTO_DATABASE_URL", DEFAULT_DATABASE_URL)

_lock = threading.Lock()
# One hub for the whole server, so the corner preview shares the camera the source reads.
_hub = camera.CameraHub()
_platform: Platform | None = None
_source: Source | None = None


def make_world(nickname: str) -> World:
    """A session for this learner. There is one desk, so every session shares one source.

    The database and the camera are opened on the first connection, not on import, so
    importing this module has no side effects.
    """
    global _platform, _source
    with _lock:
        if _platform is None:
            _platform = open_platform(database_url=DATABASE_URL)
        if _source is None:
            _source = open_source(SOURCE, _platform.layout, hub=_hub)
        return _platform.new_session(nickname=nickname, source=_source, source_name=SOURCE)


app = create_app(make_world, source=SOURCE)
if SOURCE == "camera":
    app.include_router(preview_router(_hub))
