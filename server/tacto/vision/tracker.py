"""Keep hold of where the mat is while a hand is over one of its corner markers.

`flatten` needs all four corners in the same frame, and a learner's arm covers one most
of the time they are building. The camera and the paper do not move, so the last
position found with four corners is still right, as long as the corners that can be
seen are still where that position says they should be.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable

import numpy as np

from .flatten import Flattened, fit_frame_to_page, seen_corners, warp
from .print_geometry import CORNER_MARKER_IDS, PrintGeometry

# TODO(Katie): tune on the real desk. A visible corner further than this from where the
# held position puts it means the paper or the camera moved. Marker centres jitter by
# well under a millimetre from frame to frame; a nudge of the sheet is several.
MOVED_MM = 4.0
# With every corner covered there is no evidence either way: trust the position this long.
BLIND_HOLD_S = 1.0


class MatTracker:
    """Flattens each frame, holding the last four-corner position through covered corners."""

    def __init__(
        self, geometry: PrintGeometry, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._geometry = geometry
        self._clock = clock
        self._frame_to_page: np.ndarray | None = None
        self._last_evidence_s = 0.0
        self.held = False  # the last answer used a remembered position
        self.corners_seen: list[int] = []

    def see(self, frame: np.ndarray) -> Flattened | None:
        """The page square-on, or None when the mat's position is not known."""
        self.held = False
        corners = seen_corners(frame)
        self.corners_seen = sorted(corners or {})
        if corners is None:
            return None
        fresh = fit_frame_to_page(corners, self._geometry)
        if fresh is not None:
            self._frame_to_page = fresh
            self._last_evidence_s = self._clock()
            return warp(frame, fresh)
        if self._frame_to_page is None:
            return None
        if corners:
            if self._moved(corners):
                self._frame_to_page = None
                return None
            self._last_evidence_s = self._clock()
        elif self._clock() - self._last_evidence_s > BLIND_HOLD_S:
            self._frame_to_page = None
            return None
        self.held = True
        return warp(frame, self._frame_to_page)

    def _moved(self, corners: dict[int, tuple[float, float]]) -> bool:
        expected_mm = dict(
            zip(CORNER_MARKER_IDS, self._geometry.corner_marker_centres_mm(), strict=True)
        )
        for marker_id, (x_px, y_px) in corners.items():
            x, y, w = self._frame_to_page @ np.array([x_px, y_px, 1.0])
            if abs(w) < 1e-12:
                return True
            if math.dist((x / w, y / w), expected_mm[marker_id]) > MOVED_MM:
                return True
        return False
