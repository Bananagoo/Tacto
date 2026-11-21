"""Tacto server. Run with `make dev` (uvicorn tacto.main:app --reload --port 8000).

TACTO_SOURCE picks where the world comes from:
  replay  recorded frames from server/fixtures/   (not built yet)
  camera  the LogiInsight camera                  (not built yet)

Until one of those exists, use `make bench`: the same product on a virtual mat.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .app import create_app
from .world import World

load_dotenv()

SOURCE = os.getenv("TACTO_SOURCE", "replay")


def make_world(nickname: str) -> World:
    raise NotImplementedError(
        f"TACTO_SOURCE={SOURCE} is not built yet; run `make bench` for the virtual mat"
    )


app = create_app(make_world, source=SOURCE)
