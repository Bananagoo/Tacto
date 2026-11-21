"""What the product's mat reader makes of one camera frame, for the camera bench.

This is the raw reading of a single frame, before the smoothing the product applies,
so a flickering value here is the thing to tune.
"""

from __future__ import annotations

import numpy as np

from tacto.mat.models import MatLayout
from tacto.vision.flatten import flatten
from tacto.vision.print_geometry import PrintGeometry
from tacto.vision.reader import read_mat


class FrameMatReader:
    def __init__(self, layout: MatLayout) -> None:
        self._layout = layout
        self._geometry = PrintGeometry.for_layout(layout)

    def __call__(self, frame: np.ndarray) -> dict:
        flattened = flatten(frame, self._geometry)
        if flattened is None:
            return {"found": False}
        reading = read_mat(flattened, self._layout, self._geometry)
        return {"found": True, "drawn": sorted(reading.drawn), "slots": dict(reading.slots)}
