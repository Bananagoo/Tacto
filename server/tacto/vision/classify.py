"""What is lying in a segment? The baseline answer: look at the patch's colour.

Each piece type is cut from card of one colour (`kit/pieces.yaml`). A patch is that
piece when enough of it is that colour, and empty otherwise. Black card is told by
darkness relative to the paper, so the answer does not move with the room's lighting
or the camera's exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..contract import PieceType
from ..mat import Mat
from .flatten import Flattened
from .patches import cut_patches
from .print_geometry import PrintGeometry

PieceClass = Literal["empty", "wire", "battery", "bulb", "resistor", "switch"]

COLOURS_FILE = Path(__file__).resolve().parents[3] / "kit" / "pieces.yaml"

# OpenCV stores hue as half-degrees in a byte.
_HUE_DEGREES_PER_UNIT = 2.0


class HueRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hue_deg: tuple[float, float]  # from, to, clockwise; may pass through 0

    def contains(self, hue_deg: np.ndarray) -> np.ndarray:
        start, end = (value % 360 for value in self.hue_deg)
        if start <= end:
            return (hue_deg >= start) & (hue_deg <= end)
        return (hue_deg >= start) | (hue_deg <= end)


class PieceColours(BaseModel):
    """Which colour means which piece. Loaded from `kit/pieces.yaml`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pieces: dict[PieceType, HueRange | Literal["dark"]]
    min_saturation: float = Field(0.45, gt=0, lt=1)
    dark_below: float = Field(0.35, gt=0, lt=1)
    cover_fraction: float = Field(0.5, gt=0, le=1)

    @model_validator(mode="after")
    def _at_most_one_dark_piece(self) -> PieceColours:
        if sum(rule == "dark" for rule in self.pieces.values()) > 1:
            raise ValueError("only one piece type can be the dark one")
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


def paper_brightness(page: np.ndarray) -> float:
    """How bright the paper is in this picture, 0..255.

    Most of the page is bare paper whatever is lying on it, so the median is the paper.
    """
    small = cv2.resize(page, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    return float(np.median(small.max(axis=2)))


def classify_patch(patch: np.ndarray, colours: PieceColours, *, paper: float = 255.0) -> Reading:
    """The piece whose colour covers the most of the patch, or empty if none covers enough."""
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    hue_deg = hsv[:, :, 0].astype(np.float32) * _HUE_DEGREES_PER_UNIT
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0
    # Brightness relative to the paper, so a dim room does not turn paper into black card.
    brightness = hsv[:, :, 2].astype(np.float32) / max(paper, 1.0)
    dark = brightness < colours.dark_below
    coloured = ~dark & (saturation >= colours.min_saturation)

    best: PieceClass = "empty"
    best_cover = 0.0
    for piece, rule in colours.pieces.items():
        mask = dark if rule == "dark" else coloured & rule.contains(hue_deg)
        cover = float(mask.mean())
        if cover > best_cover:
            best, best_cover = piece, cover
    if best_cover < colours.cover_fraction:
        return Reading("empty", best_cover)
    return Reading(best, best_cover)


def classify_mat(
    flattened: Flattened, mat: Mat, geometry: PrintGeometry, colours: PieceColours
) -> dict[str, Reading]:
    """Segment id -> what is lying in it, for every segment of the mat, from one frame."""
    paper = paper_brightness(flattened.image)
    return {
        segment: classify_patch(patch, colours, paper=paper)
        for segment, patch in cut_patches(flattened, mat, geometry).items()
    }
