"""Read a mat layout from its YAML file in `kit/mats/`."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import MatLayout


class MatFileError(ValueError):
    """A mat file that cannot be used. The message names the file and the problem."""


def load_mat(path: Path) -> MatLayout:
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise MatFileError(f"{path}: {error}") from error
    if not isinstance(data, dict):
        raise MatFileError(f"{path}: the top level must be a mapping")
    try:
        return MatLayout.model_validate(data)
    except ValidationError as error:
        raise MatFileError(f"{path}: {error}") from error
