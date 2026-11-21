"""Lessons and the concept graph in the database."""

import hashlib

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, delete, select

from ..lessons.models import ConceptDef, Lesson, Step
from .tables import ConceptPrerequisiteRow, ConceptRow, LessonRow, LessonStepRow


class SqlLessonRepository:
    """`repositories.LessonRepository` on a SQL database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, lesson: Lesson) -> None:
        """Insert the lesson, or replace it and its concept graph if it already exists.

        Everything happens in one transaction, so a failed save leaves the old lesson intact.
        Raises `ValueError` if one of the lesson's concepts already belongs to another lesson.
        """
        content_hash = _content_hash(lesson)
        with Session(self._engine) as session, session.begin():
            row = session.get(LessonRow, lesson.id)
            if row is not None and row.content_hash == content_hash:
                return  # the server reseeds on every start; an unchanged file writes nothing
            _reject_concepts_owned_elsewhere(session, lesson)
            if row is not None:
                _delete_content(session, lesson.id)
            session.merge(
                LessonRow(
                    id=lesson.id,
                    title=lesson.title,
                    language=lesson.language,
                    content_hash=content_hash,
                )
            )
            # Parents are written before the rows that point at them: lesson, then its
            # concepts, then the edges between concepts.
            session.flush()
            session.add_all(_step_rows(lesson))
            session.add_all(_concept_rows(lesson))
            session.flush()
            session.add_all(_prerequisite_rows(lesson))

    def get(self, lesson_id: str) -> Lesson | None:
        with Session(self._engine) as session:
            row = session.get(LessonRow, lesson_id)
            if row is None:
                return None
            steps = session.exec(
                select(LessonStepRow)
                .where(LessonStepRow.lesson_id == lesson_id)
                .order_by(col(LessonStepRow.position))
            ).all()
            concepts = session.exec(
                select(ConceptRow)
                .where(ConceptRow.lesson_id == lesson_id)
                .order_by(col(ConceptRow.position))
            ).all()
            requires = _requirements(session, lesson_id)
            return Lesson(
                id=row.id,
                title=row.title,
                language=row.language,
                concepts=[
                    ConceptDef(id=concept.id, title=concept.title, requires=requires[concept.id])
                    for concept in concepts
                ],
                steps=[Step.model_validate_json(step.body) for step in steps],
            )

    def list_ids(self) -> list[str]:
        with Session(self._engine) as session:
            return list(session.exec(select(LessonRow.id).order_by(col(LessonRow.id))).all())

    def concept_graph(self) -> dict[str, list[str]]:
        """Every known concept id -> the concept ids it requires."""
        with Session(self._engine) as session:
            return _requirements(session, lesson_id=None)


def _content_hash(lesson: Lesson) -> str:
    return hashlib.sha256(lesson.model_dump_json().encode("utf-8")).hexdigest()


def _reject_concepts_owned_elsewhere(session: Session, lesson: Lesson) -> None:
    # A concept id is one node in the learning graph, and mastery is kept per concept id,
    # so two lessons defining the same id would overwrite each other's node.
    taken = session.exec(
        select(ConceptRow)
        .where(col(ConceptRow.id).in_([concept.id for concept in lesson.concepts]))
        .where(ConceptRow.lesson_id != lesson.id)
        .order_by(col(ConceptRow.id))
    ).first()
    if taken is not None:
        raise ValueError(
            f"lesson {lesson.id!r} cannot define concept {taken.id!r}: "
            f"it already belongs to lesson {taken.lesson_id!r}"
        )


def _delete_content(session: Session, lesson_id: str) -> None:
    """Remove the lesson's steps, concepts and edges, children first."""
    own_concepts = select(ConceptRow.id).where(ConceptRow.lesson_id == lesson_id)
    session.exec(
        delete(ConceptPrerequisiteRow).where(
            col(ConceptPrerequisiteRow.concept_id).in_(own_concepts)
        )
    )
    session.exec(delete(ConceptRow).where(col(ConceptRow.lesson_id) == lesson_id))
    session.exec(delete(LessonStepRow).where(col(LessonStepRow.lesson_id) == lesson_id))


def _step_rows(lesson: Lesson) -> list[LessonStepRow]:
    return [
        LessonStepRow(
            lesson_id=lesson.id, position=position, step_id=step.id, body=step.model_dump_json()
        )
        for position, step in enumerate(lesson.steps)
    ]


def _concept_rows(lesson: Lesson) -> list[ConceptRow]:
    return [
        ConceptRow(id=concept.id, title=concept.title, lesson_id=lesson.id, position=position)
        for position, concept in enumerate(lesson.concepts)
    ]


def _prerequisite_rows(lesson: Lesson) -> list[ConceptPrerequisiteRow]:
    return [
        ConceptPrerequisiteRow(concept_id=concept.id, requires_id=requires_id, position=position)
        for concept in lesson.concepts
        for position, requires_id in enumerate(concept.requires)
    ]


def _requirements(session: Session, lesson_id: str | None) -> dict[str, list[str]]:
    """Concept id -> required concept ids, both in file order. One lesson, or all if None."""
    query = (
        select(ConceptRow.id, ConceptPrerequisiteRow.requires_id)
        .join(
            ConceptPrerequisiteRow,
            col(ConceptPrerequisiteRow.concept_id) == col(ConceptRow.id),
            isouter=True,  # a concept that requires nothing is still a node in the graph
        )
        .order_by(
            col(ConceptRow.lesson_id),
            col(ConceptRow.position),
            col(ConceptPrerequisiteRow.position),
        )
    )
    if lesson_id is not None:
        query = query.where(ConceptRow.lesson_id == lesson_id)
    graph: dict[str, list[str]] = {}
    for concept_id, requires_id in session.exec(query):
        required = graph.setdefault(concept_id, [])
        if requires_id is not None:
            required.append(requires_id)
    return graph
