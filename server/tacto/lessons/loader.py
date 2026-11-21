"""Read lesson files. YAML in `lessons/` is the authoring format; `Lesson` is what the code uses.

Lesson files are edited by hand, often minutes before a demo, so every failure is
reported as a `LessonFileError` that names the file and says what is wrong with it.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import Lesson


class LessonFileError(ValueError):
    """A lesson file could not be read or is not a valid lesson."""


def load_lesson(path: Path) -> Lesson:
    """The lesson written in one YAML file."""
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise LessonFileError(f"{path}: cannot be read: {error}") from error
    except yaml.YAMLError as error:
        raise LessonFileError(f"{path}: is not valid YAML: {error}") from error
    if not isinstance(content, dict):
        raise LessonFileError(
            f"{path}: the top level must be a mapping, found {type(content).__name__}"
        )
    try:
        return Lesson.model_validate(content)
    except ValidationError as error:
        raise LessonFileError(f"{path}: is not a valid lesson: {error}") from error


def load_lessons(directory: Path) -> list[Lesson]:
    """Every `*.yaml` lesson in the directory, sorted by file name."""
    lessons: list[Lesson] = []
    file_of: dict[str, Path] = {}
    for path in sorted(directory.glob("*.yaml")):
        lesson = load_lesson(path)
        # The lesson id is the key everywhere else, so a copied file that kept its id
        # would silently replace the original when the lessons are stored.
        if lesson.id in file_of:
            raise LessonFileError(
                f"{path}: lesson id {lesson.id!r} is already used by {file_of[lesson.id]}"
            )
        file_of[lesson.id] = path
        lessons.append(lesson)
    return lessons
