"""The database tables. Private to `store/`: nothing outside this package imports them.

Lesson content (`lesson`, `lesson_step`, `concept`, `concept_prerequisite`) is replaced
whenever a lesson file changes. Learner data (`learner`, `mastery`, `completed_step`,
`attempt`) must outlive those edits, so it refers to lessons, steps and concepts by id
without a foreign key: removing a step from a lesson never deletes what a learner did.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


class UtcDateTime(TypeDecorator[datetime]):
    """A moment in time. SQLite keeps no zone, so store UTC and hand back aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("a time without a zone cannot be stored: which moment is it?")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


class LessonRow(SQLModel, table=True):
    __tablename__ = "lesson"

    id: str = Field(primary_key=True)
    title: str
    language: str
    # Fingerprint of the whole lesson, so saving an unchanged lesson writes nothing.
    content_hash: str


class LessonStepRow(SQLModel, table=True):
    __tablename__ = "lesson_step"

    lesson_id: str = Field(primary_key=True, foreign_key="lesson.id")
    position: int = Field(primary_key=True)
    step_id: str
    body: str  # the validated step as JSON


class ConceptRow(SQLModel, table=True):
    __tablename__ = "concept"

    id: str = Field(primary_key=True)
    title: str
    lesson_id: str = Field(foreign_key="lesson.id", index=True)
    position: int  # order in the lesson file


class ConceptPrerequisiteRow(SQLModel, table=True):
    __tablename__ = "concept_prerequisite"

    concept_id: str = Field(primary_key=True, foreign_key="concept.id")
    requires_id: str = Field(primary_key=True, foreign_key="concept.id")
    position: int  # order in the concept's `requires` list


class LearnerRow(SQLModel, table=True):
    __tablename__ = "learner"

    id: int | None = Field(default=None, primary_key=True)
    nickname: str  # exactly as first typed, without surrounding spaces
    # What decides whether two nicknames are the same person: see `learners.nickname_key`.
    nickname_key: str = Field(unique=True)
    created_at: datetime = Field(default_factory=_now, sa_type=UtcDateTime)


class MasteryRow(SQLModel, table=True):
    __tablename__ = "mastery"

    learner_id: int = Field(primary_key=True, foreign_key="learner.id")
    concept_id: str = Field(primary_key=True)
    mastery: str
    correct: int
    wrong: int


class CompletedStepRow(SQLModel, table=True):
    __tablename__ = "completed_step"

    learner_id: int = Field(primary_key=True, foreign_key="learner.id")
    lesson_id: str = Field(primary_key=True)
    step_id: str = Field(primary_key=True)
    position: int  # order finished within the lesson


class AttemptRow(SQLModel, table=True):
    __tablename__ = "attempt"

    id: int | None = Field(default=None, primary_key=True)
    learner_id: int = Field(foreign_key="learner.id", index=True)
    lesson_id: str
    step_id: str
    choice: str
    correct: bool
    at: datetime = Field(sa_type=UtcDateTime)


# Every table class above registers itself here; `db.create_database` creates them from it.
metadata = SQLModel.metadata
