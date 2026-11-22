"""The printed mat: a grid of dots on a page. Its size is data, in `kit/mats/<id>.yaml`.

The kit prints from this file and the camera reads against it, so the paper and the
software cannot disagree about where a dot is.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tacto.contract import Grid

MATS_DIR = Path(__file__).resolve().parents[2] / "kit" / "mats"
DEFAULT_MAT_ID = "circuits-101"


class Mat(BaseModel):
    # A typo in a mat file should fail loudly at load time, not be ignored.
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    cols: int = Field(ge=2)  # dots across
    rows: int = Field(ge=2)  # dots down
    dot_pitch_mm: float = Field(gt=0)  # centre to centre; a piece is this long

    @property
    def grid(self) -> Grid:
        return Grid(cols=self.cols, rows=self.rows)


class MatFileError(ValueError):
    """A mat file could not be read or is not a valid mat."""


def load_mat(path: Path) -> Mat:
    """The mat in one YAML file. Errors name the file: these are edited by hand."""
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise MatFileError(f"{path}: cannot be read: {error}") from error
    except yaml.YAMLError as error:
        raise MatFileError(f"{path}: is not valid YAML: {error}") from error
    try:
        return Mat.model_validate(content)
    except ValidationError as error:
        raise MatFileError(f"{path}: is not a valid mat: {error}") from error


def load_default_mat() -> Mat:
    return load_mat(MATS_DIR / f"{DEFAULT_MAT_ID}.yaml")
