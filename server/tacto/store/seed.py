"""Put the lesson files into the database. Run at startup, so the files stay the source of truth."""

from pathlib import Path

from ..lessons.loader import load_lessons
from .repositories import LessonRepository


def seed_lessons(repository: LessonRepository, directory: Path) -> list[str]:
    """Save every lesson file in the directory; the lesson ids saved, in file order.

    Every file is read and validated before the first save, so one bad file raises
    `LessonFileError` and leaves the stored lessons exactly as they were.
    """
    lessons = load_lessons(directory)
    for lesson in lessons:
        repository.save(lesson)
    return [lesson.id for lesson in lessons]
