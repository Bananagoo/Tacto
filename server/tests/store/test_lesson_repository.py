"""Lessons and the concept graph go into the database and come back unchanged."""

from pathlib import Path

import pytest
from sqlalchemy import func
from sqlmodel import Session, select
from store_samples import make_lesson, make_step

from tacto.lessons.loader import load_lesson
from tacto.store.lessons import SqlLessonRepository
from tacto.store.repositories import LessonRepository
from tacto.store.tables import ConceptPrerequisiteRow, ConceptRow, LessonStepRow

REAL_LESSON = Path(__file__).resolve().parents[3] / "lessons" / "circuits-101.yaml"


@pytest.fixture
def lessons(engine) -> SqlLessonRepository:
    return SqlLessonRepository(engine)


def count(engine, table: type) -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(table)).one()


def test_it_satisfies_the_repository_interface(lessons):
    repository: LessonRepository = lessons  # checked by the type checker, documented here
    assert repository.list_ids() == []


def test_a_saved_lesson_reads_back_equal(lessons):
    lesson = make_lesson()

    lessons.save(lesson)

    assert lessons.get("circuits-101") == lesson


def test_the_real_lesson_reads_back_equal(lessons):
    lesson = load_lesson(REAL_LESSON)

    lessons.save(lesson)

    assert lessons.get(lesson.id) == lesson


def test_the_order_of_steps_concepts_and_requirements_is_kept(lessons):
    # Deliberately not alphabetical anywhere, so a sort on the way out would show.
    lesson = make_lesson(
        concepts=[
            {"id": "zeta", "title": "Zeta"},
            {"id": "alpha", "title": "Alpha"},
            {"id": "mid", "title": "Mid", "requires": ["zeta", "alpha"]},
        ],
        steps=[make_step("second", ["mid"]), make_step("first", ["zeta", "alpha"])],
    )

    lessons.save(lesson)

    assert lessons.get(lesson.id) == lesson


def test_an_unknown_lesson_is_none(lessons):
    lessons.save(make_lesson())

    assert lessons.get("no-such-lesson") is None


def test_lesson_ids_are_listed_sorted(lessons):
    for lesson_id, concept in (("zebra", "z"), ("apple", "a"), ("mango", "m")):
        lessons.save(
            make_lesson(
                lesson_id,
                concepts=[{"id": concept, "title": concept}],
                steps=[make_step("only", [concept])],
            )
        )

    assert lessons.list_ids() == ["apple", "mango", "zebra"]


def test_saving_a_changed_lesson_replaces_its_steps_and_concepts(lessons):
    lessons.save(make_lesson())
    changed = make_lesson(
        title="Circuits, second edition",
        concepts=[
            {"id": "closed_loop", "title": "A closed loop"},
            {"id": "voltage", "title": "Voltage", "requires": ["closed_loop"]},
        ],
        steps=[make_step("wheel", ["voltage"])],
    )

    lessons.save(changed)

    assert lessons.get("circuits-101") == changed
    assert lessons.concept_graph() == {"closed_loop": [], "voltage": ["closed_loop"]}


def test_saving_the_same_lesson_twice_leaves_no_orphan_rows(engine, lessons):
    lesson = make_lesson()

    lessons.save(lesson)
    lessons.save(lesson)

    assert count(engine, LessonStepRow) == len(lesson.steps)
    assert count(engine, ConceptRow) == len(lesson.concepts)
    assert count(engine, ConceptPrerequisiteRow) == sum(len(c.requires) for c in lesson.concepts)


def test_replacing_a_lesson_leaves_no_orphan_rows(engine, lessons):
    lessons.save(make_lesson())
    smaller = make_lesson(
        concepts=[{"id": "closed_loop", "title": "Closed loop"}],
        steps=[make_step("close_the_loop", ["closed_loop"])],
    )

    lessons.save(smaller)

    assert count(engine, LessonStepRow) == 1
    assert count(engine, ConceptRow) == 1
    assert count(engine, ConceptPrerequisiteRow) == 0


def test_the_concept_graph_has_every_concept_with_its_requirements(lessons):
    lessons.save(make_lesson())
    lessons.save(
        make_lesson(
            "magnets-101",
            concepts=[
                {"id": "field", "title": "Field"},
                {"id": "induction", "title": "Induction", "requires": ["field"]},
            ],
            steps=[make_step("only", ["induction"])],
        )
    )

    assert lessons.concept_graph() == {
        "closed_loop": [],
        "current": ["closed_loop"],
        "series": ["current", "closed_loop"],
        "field": [],
        "induction": ["field"],
    }


def test_replacing_one_lesson_leaves_the_others_alone(lessons):
    magnets = make_lesson(
        "magnets-101",
        concepts=[{"id": "field", "title": "Field"}],
        steps=[make_step("only", ["field"])],
    )
    lessons.save(make_lesson())
    lessons.save(magnets)

    lessons.save(make_lesson(title="Circuits, second edition"))

    assert lessons.get("magnets-101") == magnets
    assert lessons.list_ids() == ["circuits-101", "magnets-101"]


def test_a_concept_cannot_belong_to_two_lessons(lessons):
    lessons.save(make_lesson())
    clash = make_lesson(
        "magnets-101",
        concepts=[{"id": "current", "title": "Current again"}],
        steps=[make_step("only", ["current"])],
    )

    with pytest.raises(ValueError, match="current.*circuits-101"):
        lessons.save(clash)

    # The failed save left nothing behind.
    assert lessons.list_ids() == ["circuits-101"]
    assert lessons.get("circuits-101") == make_lesson()
