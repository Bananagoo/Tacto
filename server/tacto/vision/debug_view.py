"""What the camera reader sees, drawn for a person: the flattened mat with each segment's
reading written beside it. Used by the setup check's live view (GET /setup/view) and by the
camera bench. Nothing is stored: pictures are drawn and sent, never written to disk.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..contract import segment_id
from ..mat import Mat
from .classify import Reading
from .flatten import FLAT_DPI
from .patches import segments
from .print_geometry import PrintGeometry, mm_to_px

# What the debug view writes on each segment, and in which colour (blue, green, red).
_LABELS: dict[str, tuple[str, tuple[int, int, int]]] = {
    "wire": ("W", (210, 70, 30)),
    "bulb": ("Bu", (0, 140, 200)),
    "resistor": ("R", (170, 0, 215)),
    "switch_closed": ("Sc", (50, 140, 20)),
    "switch_open": ("So", (160, 130, 0)),
    "battery": ("Ba", (20, 20, 220)),
    "unsure": ("?", (120, 120, 120)),
}


def draw_readings(
    page: np.ndarray, readings: dict[str, Reading], mat: Mat, geometry: PrintGeometry
) -> np.ndarray:
    """The flattened mat with each segment's reading written beside it: the piece, how much
    of the patch showed its colour, and a + at a battery's positive end."""
    drawn = page.copy()
    px_per_mm = mm_to_px(1.0, dpi=FLAT_DPI)
    for a, b in segments(mat):
        reading = readings.get(segment_id(a, b))
        if reading is None or reading.piece == "empty":
            continue
        (ax, ay), (bx, by) = geometry.dot_mm(a), geometry.dot_mm(b)
        text, colour = _LABELS[reading.piece]
        x, y = (ax + bx) / 2 * px_per_mm, (ay + by) / 2 * px_per_mm
        runs_down = a[0] == b[0]
        # Beside the piece, not on it: below a piece lying across, right of one lying down.
        at = (round(x + 24), round(y + 6)) if runs_down else (round(x - 22), round(y + 34))
        label = f"{text} {round(reading.cover * 100)}"
        cv2.putText(drawn, label, at, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 4)
        cv2.putText(drawn, label, at, cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
        if reading.positive is not None:
            px, py = (ax, ay) if reading.positive == "a" else (bx, by)
            plus = (round(px * px_per_mm) - 8, round(py * px_per_mm) - 8)
            cv2.putText(drawn, "+", plus, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 5)
            cv2.putText(drawn, "+", plus, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 220), 2)
    return drawn


def placeholder(width: int, height: int, words: str) -> np.ndarray:
    """A plain grey picture with a line of text, for when there is nothing to show."""
    picture = np.full((height, width, 3), 40, np.uint8)
    size = cv2.getTextSize(words, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
    at = ((width - size[0]) // 2, (height + size[1]) // 2)
    cv2.putText(picture, words, at, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (220, 220, 220), 2, cv2.LINE_AA)
    return picture


def encode_jpeg(picture: np.ndarray, width: int, quality: int = 75) -> bytes:
    """JPEG bytes, scaled down to `width`."""
    if 0 < width < picture.shape[1]:
        height = round(picture.shape[0] * width / picture.shape[1])
        picture = cv2.resize(picture, (width, height), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", picture, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("could not encode the picture")
    return encoded.tobytes()


def camera_view(frame: np.ndarray | None) -> np.ndarray:
    """The camera's own picture for the setup check, or a placeholder before the first frame."""
    if frame is None:
        return placeholder(1280, 720, "Waiting for the camera")
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    return frame


def setup_view(look: tuple[np.ndarray, dict] | None, mat: Mat) -> np.ndarray:
    """The setup check's live view: the flattened mat with its readings, or a placeholder."""
    if look is None:
        return placeholder(1169, 827, "Mat not found: clear the four corner squares")
    page, readings = look
    return draw_readings(page, readings, mat, PrintGeometry.for_mat(mat))
