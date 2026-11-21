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

from dataclasses import dataclass
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
# A square is measured against the paper just round it, not the page's: the squares are at
# the edge nearest the learner, and an arm's shadow over them must not change what colour
# they are taken to be. The paper is looked for in a frame this far outside the square ...
SQUARE_PAPER_FROM_MM = 1.5
SQUARE_PAPER_TO_MM = 4.0
# ... and must still look like paper: no darker than this share of the page's paper (a
# shadow is, a sleeve is not), and nearly colourless once the page's colour is divided out.
SQUARE_PAPER_MIN_LIGHT = 0.4
SQUARE_PAPER_MAX_CHROMA = 12.0

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
    page: np.ndarray, paper: np.ndarray, geometry: PrintGeometry, mat: Mat, previous: Palette
) -> Palette:
    """The palette with every square that can be trusted in this frame read afresh.
    `page` is the flattened mat as the camera gave it; `paper` is its `paper_colour`."""
    px_per_mm = mm_to_px(1.0, dpi=FLAT_DPI)
    half_px = REFERENCE_SQUARE_MM * SQUARE_SAMPLED_FRACTION / 2 * px_per_mm
    inner_px = (REFERENCE_SQUARE_MM / 2 + SQUARE_PAPER_FROM_MM) * px_per_mm
    outer_px = (REFERENCE_SQUARE_MM / 2 + SQUARE_PAPER_TO_MM) * px_per_mm
    height_px, width_px = page.shape[:2]
    lab, seen = previous.lab.copy(), list(previous.seen)
    for name, (x_mm, y_mm) in geometry.reference_square_centres_mm(mat.cols).items():
        index = _NAMES.index(name)
        x_px, y_px = x_mm * px_per_mm, y_mm * px_per_mm
        left, right = round(x_px - outer_px), round(x_px + outer_px)
        top, bottom = round(y_px - outer_px), round(y_px + outer_px)
        if left < 0 or top < 0 or right > width_px or bottom > height_px:
            continue
        around = page[top:bottom, left:right]
        # The frame of paper round the square: everything in the box but its middle.
        ys, xs = np.mgrid[top:bottom, left:right]
        frame = (np.abs(xs - x_px) > inner_px) | (np.abs(ys - y_px) > inner_px)
        local_paper = np.maximum(np.median(around[frame], axis=0), 1.0).astype(np.float32)
        as_lab = to_lab(local_paper[None, None, :], paper)[0, 0]
        if (
            float(local_paper.max() / paper.max()) < SQUARE_PAPER_MIN_LIGHT
            or float(np.hypot(as_lab[1], as_lab[2])) > SQUARE_PAPER_MAX_CHROMA
        ):
            continue  # that is not paper round the square: something is lying there
        crop = page[
            round(y_px - half_px) : round(y_px + half_px),
            round(x_px - half_px) : round(x_px + half_px),
        ]
        pixels = to_lab(crop, local_paper).reshape(-1, 3)
        if float(pixels.std(axis=0).max()) > SQUARE_EVEN_WITHIN:
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
    weights = np.float32([LIGHTNESS_WEIGHT, 1.0, 1.0])
    weighted = flat * weights
    # One colour at a time, on squared distances: several times quicker than one big
    # pixels-by-colours table, and this runs on every frame.
    nearest = np.full(len(flat), _OTHER, dtype=np.intp)
    nearest_squared = np.full(len(flat), MAX_COLOUR_DISTANCE**2, dtype=np.float32)
    for index, reference in enumerate(palette.lab.astype(np.float32) * weights):
        if index == _NEGATIVE:
            continue  # black has no colour of its own to match; it is told by darkness below
        offset = weighted - reference
        squared = np.einsum("ij,ij->i", offset, offset)
        closer = squared <= nearest_squared
        nearest[closer] = index
        nearest_squared[closer] = squared[closer]
    labels = nearest
    neutral = np.hypot(flat[:, 1], flat[:, 2]) < NEUTRAL_CHROMA
    # Halfway between the black square and white paper: darker is ink, lighter is paper.
    dark = flat[:, 0] < (palette.lab[_NEGATIVE, 0] + 100.0) / 2
    labels = np.where(neutral, np.where(dark, _NEGATIVE, _PAPER), labels)
    return labels.reshape(lab.shape[:2])


def classify_patch(lab_patch: np.ndarray, palette: Palette, colours: PieceColours) -> Reading:
    """What one patch shows. The patch is CIELAB (see `to_lab`) and runs from dot a to dot b."""
    return classify_labels(label_pixels(lab_patch, palette), colours)


def classify_labels(labels: np.ndarray, colours: PieceColours) -> Reading:
    """What one patch shows, from its pixels' labels (see `label_pixels`)."""
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
        paper = paper_colour(flattened.image)
        self.palette = read_squares(flattened.image, paper, self.geometry, self.mat, self.palette)
        patches = cut_patches(flattened, self.mat, self.geometry)
        if not patches:
            return {}
        # Only the patches are converted and labelled, not the whole page, and all in one
        # pass: they are the same size, and together a fourteenth of the page.
        stacked = np.stack(list(patches.values()))
        count, height, width = stacked.shape[:3]
        lab = to_lab(stacked.reshape(count * height, width, 3), paper)
        labels = label_pixels(lab, self.palette)
        return {
            segment: classify_labels(patch_labels, self._colours)
            for segment, patch_labels in zip(
                patches, labels.reshape(count, height, width), strict=True
            )
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
