"""Learners in the database: a nickname, mastery per concept, steps finished, predictions made."""

import unicodedata

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, delete, select

from ..learner.models import Attempt, ConceptProgress, Progress
from .tables import AttemptRow, CompletedStepRow, LearnerRow, MasteryRow


def nickname_key(nickname: str) -> str:
    """What makes two typed nicknames the same learner: spaces around it and case do not count.

    Normalising first means a letter typed as one character and the same letter typed
    with a separate accent give the same key.
    """
    return unicodedata.normalize("NFC", nickname.strip()).casefold()


class SqlLearnerRepository:
    """`repositories.LearnerRepository` on a SQL database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_or_create(self, nickname: str) -> int:
        """The learner's id. Raises `ValueError` for a nickname that is empty or only spaces."""
        key = nickname_key(nickname)
        if not key:
            raise ValueError("a learner's nickname cannot be empty")
        with Session(self._engine) as session, session.begin():
            learner = session.exec(select(LearnerRow).where(LearnerRow.nickname_key == key)).first()
            if learner is None:
                learner = LearnerRow(nickname=nickname.strip(), nickname_key=key)
                session.add(learner)
                session.flush()  # the database chooses the id
            assert learner.id is not None
            return learner.id

    def load_progress(self, learner_id: int) -> Progress:
        with Session(self._engine) as session:
            mastery_rows = session.exec(
                select(MasteryRow).where(MasteryRow.learner_id == learner_id)
            ).all()
            step_rows = session.exec(
                select(CompletedStepRow)
                .where(CompletedStepRow.learner_id == learner_id)
                .order_by(col(CompletedStepRow.lesson_id), col(CompletedStepRow.position))
            ).all()
        completed_steps: dict[str, list[str]] = {}
        for row in step_rows:
            completed_steps.setdefault(row.lesson_id, []).append(row.step_id)
        return Progress(
            concepts={
                row.concept_id: ConceptProgress(
                    mastery=row.mastery, correct=row.correct, wrong=row.wrong
                )
                for row in mastery_rows
            },
            completed_steps=completed_steps,
        )

    def save_progress(self, learner_id: int, progress: Progress) -> None:
        """Replace everything stored about the learner's progress, in one transaction.

        A lesson with no finished steps has no rows, so it is not there when loaded back.
        """
        with Session(self._engine) as session, session.begin():
            session.exec(delete(MasteryRow).where(col(MasteryRow.learner_id) == learner_id))
            session.exec(
                delete(CompletedStepRow).where(col(CompletedStepRow.learner_id) == learner_id)
            )
            session.add_all(
                MasteryRow(
                    learner_id=learner_id,
                    concept_id=concept_id,
                    mastery=concept.mastery,
                    correct=concept.correct,
                    wrong=concept.wrong,
                )
                for concept_id, concept in progress.concepts.items()
            )
            session.add_all(
                CompletedStepRow(
                    learner_id=learner_id, lesson_id=lesson_id, step_id=step_id, position=position
                )
                for lesson_id, step_ids in progress.completed_steps.items()
                for position, step_id in enumerate(step_ids)
            )

    def record_attempt(self, learner_id: int, attempt: Attempt) -> None:
        """Keep one prediction. Raises `ValueError` if its time has no zone."""
        if attempt.at.tzinfo is None:
            raise ValueError("an attempt's time needs a zone, or the moment it names is a guess")
        with Session(self._engine) as session, session.begin():
            session.add(
                AttemptRow(
                    learner_id=learner_id,
                    lesson_id=attempt.lesson_id,
                    step_id=attempt.step_id,
                    choice=attempt.choice,
                    correct=attempt.correct,
                    at=attempt.at,
                )
            )

    def attempts(self, learner_id: int) -> list[Attempt]:
        """Oldest first; attempts at the same moment in the order they were recorded."""
        with Session(self._engine) as session:
            rows = session.exec(
                select(AttemptRow)
                .where(AttemptRow.learner_id == learner_id)
                .order_by(col(AttemptRow.at), col(AttemptRow.id))
            ).all()
        return [
            Attempt(
                lesson_id=row.lesson_id,
                step_id=row.step_id,
                choice=row.choice,
                correct=row.correct,
                at=row.at,
            )
            for row in rows
        ]
