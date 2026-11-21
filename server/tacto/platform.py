"""Assemble the product from its parts: database, lessons, mat, and sessions for learners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lessons.models import Lesson
from .mat.loader import load_mat
from .mat.models import MatLayout
from .observation import Source
from .session import Session
from .store.db import DEFAULT_DATABASE_URL, create_database
from .store.learners import SqlLearnerRepository
from .store.lessons import SqlLessonRepository
from .store.repositories import LearnerRepository
from .store.seed import seed_lessons

REPO_ROOT = Path(__file__).resolve().parents[2]
LESSONS_DIR = REPO_ROOT / "lessons"
MATS_DIR = REPO_ROOT / "kit" / "mats"
DEFAULT_LESSON_ID = "circuits-101"
DEFAULT_NICKNAME = "guest"


@dataclass(frozen=True)
class Platform:
    """Everything a session needs that outlives it."""

    lesson: Lesson
    layout: MatLayout
    learners: LearnerRepository

    def new_session(self, *, nickname: str, source: Source, source_name: str) -> Session:
        return Session(
            lesson=self.lesson,
            layout=self.layout,
            source=source,
            source_name=source_name,
            learner_id=self.learners.get_or_create(nickname),
            learners=self.learners,
        )


def open_platform(
    *,
    database_url: str = DEFAULT_DATABASE_URL,
    lesson_id: str = DEFAULT_LESSON_ID,
    lessons_dir: Path = LESSONS_DIR,
    mats_dir: Path = MATS_DIR,
) -> Platform:
    """Open the database, load the lesson files into it, and pick the lesson to teach.

    A lesson's mat is the file with the same id in `mats_dir`.
    """
    engine = create_database(database_url)
    lessons = SqlLessonRepository(engine)
    seed_lessons(lessons, lessons_dir)
    lesson = lessons.get(lesson_id)
    if lesson is None:
        raise LookupError(f"no lesson {lesson_id!r}; known lessons: {lessons.list_ids()}")
    return Platform(
        lesson=lesson,
        layout=load_mat(mats_dir / f"{lesson_id}.yaml"),
        learners=SqlLearnerRepository(engine),
    )
