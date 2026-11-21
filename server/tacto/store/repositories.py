"""What the product needs from storage. The SQLite implementations live beside this file.

Code outside `store/` depends on these interfaces only, so storage can change
(another database, an in-memory fake in tests) without touching it.
"""

from __future__ import annotations

from typing import Protocol

from ..learner.models import Attempt, Progress
from ..lessons.models import Lesson


class LessonRepository(Protocol):
    def save(self, lesson: Lesson) -> None:
        """Insert the lesson, or replace it and its concept graph if it already exists."""
        ...

    def get(self, lesson_id: str) -> Lesson | None: ...

    def list_ids(self) -> list[str]: ...

    def concept_graph(self) -> dict[str, list[str]]:
        """Every known concept id -> the concept ids it requires."""
        ...


class LearnerRepository(Protocol):
    def get_or_create(self, nickname: str) -> int:
        """The learner's id. A nickname is all we keep about a person."""
        ...

    def load_progress(self, learner_id: int) -> Progress: ...

    def save_progress(self, learner_id: int, progress: Progress) -> None: ...

    def record_attempt(self, learner_id: int, attempt: Attempt) -> None: ...

    def attempts(self, learner_id: int) -> list[Attempt]:
        """Oldest first."""
        ...
