"""What is lying in a segment? Match its patch to the colour squares printed on the mat.

Each printed piece is one colour (`kit/pieces.yaml`); the battery is two, red at its
positive end and black at its negative. The mat carries a square of every one of those
colours. The reader samples the squares in each frame and gives every pixel of a patch
to the nearest of them, so the answer follows the room's light, the camera's exposure
and its colour cast instead of fixed colour ranges. On the demo desk the camera sees
cyan and blue only 22 degrees of hue apart and magenta and red 26 (docs/hardware-log.md).

Colours are compared after dividing by the paper's colour, which makes the paper white
whatever the light, and in CIELAB, where equal distances look about equally different.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..mat import Mat
from ..pieces import Placed
from .flatten import FLAT_DPI, Flattened
from .patches import cut_patches, segments
from .print_geometry import REFERENCE_SQUARE_MM, REFERENCE_SQUARES, PrintGeometry, mm_to_px

PieceClass = Literal[
    "empty", "wire", "bulb", "resistor", "switch_closed", "switch_open", "battery", "unsure"
]
ColourName = Literal[
    "wire",
    "bulb",
    "resistor",
    "switch_closed",
    "switch_open",
    "battery_positive",
    "battery_negative",
]

COLOURS_FILE = Path(__file__).resolve().parents[3] / "kit" / "pieces.yaml"

# TODO(Katie): the numbers below were chosen from one desk on 21 Nov 2026. Recheck at the venue.
# Lightness counts for less than colour when comparing: a shadow changes it, not the hue.
LIGHTNESS_WEIGHT = 0.5
# A pixel further than this from every piece colour is "something else" (skin, a sleeve).
MAX_COLOUR_DISTANCE = 45.0
# A pixel with less colour than this is paper, a shadow, a printed dot or black ink.
NEUTRAL_CHROMA = 14.0
# Each battery half must be at least this much of the patch for the two to be a battery.
BATTERY_HALF_FRACTION = 0.1
# A reference square is believed only if it is one even colour ...
SQUARE_EVEN_WITHIN = 9.0
# ... a real colour, not skin or shadow (the palest square on the desk read about 50) ...
SQUARE_MIN_CHROMA = 32.0
SQUARE_BLACK_MAX_LIGHTNESS = 50.0
# ... and close to what it read last time: the light changes slowly, a hand arrives at once.
SQUARE_MAX_JUMP = 20.0
# The middle half of a square is sampled, clear of its edge and of a millimetre of misfit.
SQUARE_SAMPLED_FRACTION = 0.5

_NAMES: tuple[ColourName, ...] = REFERENCE_SQUARES  # type: ignore[assignment]
_POSITIVE = _NAMES.index("battery_positive")
_NEGATIVE = _NAMES.index("battery_negative")
_PAPER = len(_NAMES)
_OTHER = len(_NAMES) + 1
_SINGLE_COLOUR_PIECES: tuple[PieceClass, ...] = (
    "wire",
    "bulb",
    "resistor",
    "switch_closed",
    "switch_open",
)


class PieceColours(BaseModel):
    """The printed colour of each piece, and how much of a patch must show it.
    Loaded from `kit/pieces.yaml`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    colours: dict[ColourName, tuple[int, int, int]]  # red, green, blue as printed
    cover_fraction: float = Field(0.35, gt=0, le=1)
    unsure_fraction: float = Field(0.18, gt=0, le=1)
    covered_fraction: float = Field(0.3, gt=0, le=1)

    @model_validator(mode="after")
    def _complete_and_ordered(self) -> PieceColours:
        missing = [name for name in _NAMES if name not in self.colours]
        if missing:
            raise ValueError(f"no colour given for: {', '.join(missing)}")
        if any(not 0 <= value <= 255 for colour in self.colours.values() for value in colour):
            raise ValueError("colour values run from 0 to 255")
        if self.unsure_fraction >= self.cover_fraction:
            raise ValueError("unsure_fraction must be below cover_fraction")
        return self


class ColoursFileError(ValueError):
    """The piece colours file could not be read or is not valid."""


def load_colours(path: Path = COLOURS_FILE) -> PieceColours:
    try:
        return PieceColours.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ColoursFileError(f"{path}: cannot be read: {error}") from error
    except ValidationError as error:
        raise ColoursFileError(f"{path}: is not a valid colours file: {error}") from error


@dataclass(frozen=True)
class Reading:
    """What one segment's patch looks like."""

    piece: PieceClass
    cover: float  # the fraction of the patch that is the winning piece's colour, 0..1
    positive: Literal["a", "b"] | None = None  # batteries only: which dot the red half is at


@dataclass(frozen=True)
class Palette:
    """What each piece colour looks like right now, in paper-white CIELAB."""

    lab: np.ndarray  # one row per colour, in REFERENCE_SQUARES order
    seen: tuple[bool, ...]  # False: this row is still the printed value, not a reading


def paper_colour(page: np.ndarray) -> np.ndarray:
    """The paper's colour in this picture, blue, green, red.

    Most of the page is bare paper whatever is lying on it, so the median is the paper.
    """
    small = cv2.resize(page, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    return np.maximum(np.median(small.reshape(-1, 3), axis=0), 1.0).astype(np.float32)


def to_lab(picture: np.ndarray, paper: np.ndarray) -> np.ndarray:
    """A BGR picture as CIELAB with the paper as white: paper is (100, 0, 0) in any light."""
    return cv2.cvtColor(np.clip(picture.astype(np.float32) / paper, 0.0, 1.0), cv2.COLOR_BGR2Lab)


def printed_palette(colours: PieceColours) -> Palette:
    """The colours as the sheet defines them: the starting point before any square is read."""
    bgr = np.float32([[colours.colours[name][::-1] for name in _NAMES]])
    lab = to_lab(bgr, np.float32([255.0, 255.0, 255.0]))[0]
    return Palette(lab=lab, seen=(False,) * len(_NAMES))


def read_squares(
    lab_page: np.ndarray, geometry: PrintGeometry, mat: Mat, previous: Palette
) -> Palette:
    """The palette with every square that can be trusted in this frame read afresh."""
    px_per_mm = mm_to_px(1.0, dpi=FLAT_DPI)
    half_px = REFERENCE_SQUARE_MM * SQUARE_SAMPLED_FRACTION / 2 * px_per_mm
    lab, seen = previous.lab.copy(), list(previous.seen)
    for name, (x_mm, y_mm) in geometry.reference_square_centres_mm(mat.cols).items():
        index = _NAMES.index(name)
        x_px, y_px = x_mm * px_per_mm, y_mm * px_per_mm
        pixels = lab_page[
            round(y_px - half_px) : round(y_px + half_px),
            round(x_px - half_px) : round(x_px + half_px),
        ].reshape(-1, 3)
        if pixels.size == 0 or float(pixels.std(axis=0).max()) > SQUARE_EVEN_WITHIN:
            continue
        sample = np.median(pixels, axis=0)
        chroma = float(np.hypot(sample[1], sample[2]))
        if index == _NEGATIVE:
            real = sample[0] <= SQUARE_BLACK_MAX_LIGHTNESS and chroma < SQUARE_MIN_CHROMA
        else:
            real = chroma >= SQUARE_MIN_CHROMA
        if not real:
            continue
        if seen[index] and float(np.linalg.norm(sample - lab[index])) > SQUARE_MAX_JUMP:
            continue
        lab[index], seen[index] = sample, True
    return Palette(lab=lab, seen=tuple(seen))


def label_pixels(lab: np.ndarray, palette: Palette) -> np.ndarray:
    """For every pixel: the index of its piece colour, or `_PAPER`, or `_OTHER`."""
    flat = lab.reshape(-1, 3)
    difference = flat[:, None, :] - palette.lab[None, :, :]
    difference[:, :, 0] *= LIGHTNESS_WEIGHT
    distance = np.linalg.norm(difference, axis=2)
    # Black has no colour of its own to match, so it is told by darkness further down.
    distance[:, _NEGATIVE] = np.inf
    nearest = distance.argmin(axis=1)
    labels = np.where(distance.min(axis=1) <= MAX_COLOUR_DISTANCE, nearest, _OTHER)
    neutral = np.hypot(flat[:, 1], flat[:, 2]) < NEUTRAL_CHROMA
    # Halfway between the black square and white paper: darker is ink, lighter is paper.
    dark = flat[:, 0] < (palette.lab[_NEGATIVE, 0] + 100.0) / 2
    labels = np.where(neutral, np.where(dark, _NEGATIVE, _PAPER), labels)
    return labels.reshape(lab.shape[:2])


def classify_patch(lab_patch: np.ndarray, palette: Palette, colours: PieceColours) -> Reading:
    """What one patch shows. The patch is CIELAB (see `to_lab`) and runs from dot a to dot b."""
    labels = label_pixels(lab_patch, palette)
    fraction = np.bincount(labels.ravel(), minlength=_OTHER + 1) / labels.size

    best: PieceClass = "empty"
    best_cover = 0.0
    for piece in _SINGLE_COLOUR_PIECES:
        cover = float(fraction[_NAMES.index(piece)])
        if cover > best_cover:
            best, best_cover = piece, cover
    positive: Literal["a", "b"] | None = None
    red, black = float(fraction[_POSITIVE]), float(fraction[_NEGATIVE])
    if min(red, black) >= BATTERY_HALF_FRACTION and red + black > best_cover:
        best, best_cover = "battery", red + black
        along = np.arange(labels.shape[1])[None, :].repeat(labels.shape[0], axis=0)
        red_at, black_at = along[labels == _POSITIVE].mean(), along[labels == _NEGATIVE].mean()
        positive = "a" if red_at < black_at else "b"
    elif red > best_cover:
        # Red with no black beside it: half a battery, or one lying mostly out of the patch.
        # Enough of it is worth holding the last answer for; it is never a piece by itself.
        return Reading("unsure" if red >= colours.unsure_fraction else "empty", red)

    if fraction[_OTHER] >= colours.covered_fraction:
        return Reading("unsure", best_cover)
    if best_cover >= colours.cover_fraction:
        return Reading(best, best_cover, positive)
    if best_cover >= colours.unsure_fraction:
        return Reading("unsure", best_cover)
    return Reading("empty", best_cover)


class MatReader:
    """Reads every segment of a flattened mat, remembering what the colour squares look like."""

    def __init__(self, mat: Mat, geometry: PrintGeometry, colours: PieceColours) -> None:
        self.mat = mat
        self.geometry = geometry
        self._colours = colours
        self.palette = printed_palette(colours)

    def read(self, flattened: Flattened) -> dict[str, Reading]:
        """Segment id -> what is lying in it, for every segment of the mat, from one frame."""
        lab_page = to_lab(flattened.image, paper_colour(flattened.image))
        self.palette = read_squares(lab_page, self.geometry, self.mat, self.palette)
        patches = cut_patches(replace(flattened, image=lab_page), self.mat, self.geometry)
        return {
            segment: classify_patch(patch, self.palette, self._colours)
            for segment, patch in patches.items()
        }


def to_placed(readings: dict[str, Reading], mat: Mat) -> tuple[Placed, ...]:
    """The pieces a set of readings amounts to, in segment order. Unsure and empty are left out."""
    placed: list[Placed] = []
    for a, b in segments(mat):
        reading = readings.get(Placed("wire", a, b).id)
        if reading is None or reading.piece in ("empty", "unsure"):
            continue
        if reading.piece == "battery":
            plus, minus = (a, b) if reading.positive != "b" else (b, a)
            placed.append(Placed("battery", plus, minus))
        elif reading.piece in ("switch_closed", "switch_open"):
            placed.append(Placed("switch", a, b, closed=reading.piece == "switch_closed"))
        else:
            placed.append(Placed(reading.piece, a, b))
    return tuple(placed)
