"""The lab server. Run with `make dev` (uvicorn tacto.main:app --port 8000).

TACTO_SOURCE picks where the mat comes from:
  camera  the camera above the printed mat (default)
  replay  frames recorded into server/fixtures/<mat id>/

The camera reader is being rebuilt for pieces without markers (colour patches per
segment). Until it lands, neither source can start: use `make manual`, which runs
the same lab on a mat set by hand.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

SOURCE = os.getenv("TACTO_SOURCE", "camera")

raise SystemExit(
    f"main: TACTO_SOURCE={SOURCE!r} cannot start yet: the camera reader for unmarked "
    "pieces is not built. Run `make manual` for the lab on a hand-set mat, or "
    "`make mock` to replay the recorded sample."
)
