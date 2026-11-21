"""At startup every lesson file is loaded into the database."""

from pathlib import Path

import pytest
from store_samples import make_lesson

from tacto.lessons.loader import LessonFileError, load_lesson
from tacto.store.lessons import SqlLessonRepository
from tacto.store.seed import seed_lessons

LESSONS_DIRECTORY = Path(__file__).resolve().parents[3] / "lessons"


@pytest.fixture
def lessons(engine) -> SqlLessonRepository:
    return SqlLessonRepository(engine)


def write_lesson(directory: Path, file_name: str, lesson_id: str, concept_id: str) -> None:
    lesson = make_lesson(
        lesson_id,
        concepts=[{"id": concept_id, "title": concept_id}],
        steps=[
            {
                "id": "only",
                "teaches": [concept_id],
                "build": {"say": "Close the loop.", "done_when": {"status": "closed"}},
                "observe": {"say": "Touch a wire."},
                "explain": {"say": "Current needs a closed loop."},
            }
        ],
    )
    # JSON is YAML, so the model's own dump is a valid lesson file.
    (directory / file_name).write_text(lesson.model_dump_json(), encoding="utf-8")


def test_the_real_lessons_are_seeded(lessons):
    saved = seed_lessons(lessons, LESSONS_DIRECTORY)

    assert "circuits-101" in saved
    assert lessons.get("circuits-101") == load_lesson(LESSONS_DIRECTORY / "circuits-101.yaml")


def test_seeding_twice_leaves_one_copy_of_each_lesson(lessons):
    first = seed_lessons(lessons, LESSONS_DIRECTORY)
    second = seed_lessons(lessons, LESSONS_DIRECTORY)

    assert first == second
    assert lessons.list_ids() == sorted(first)
    assert lessons.get("circuits-101") == load_lesson(LESSONS_DIRECTORY / "circuits-101.yaml")


def test_the_ids_saved_are_returned_in_file_order(lessons, tmp_path):
    write_lesson(tmp_path, "b.yaml", "written-second", "beta")
    write_lesson(tmp_path, "a.yaml", "written-first", "alpha")

    assert seed_lessons(lessons, tmp_path) == ["written-first", "written-second"]


def test_an_edited_file_replaces_the_stored_lesson(lessons, tmp_path):
    write_lesson(tmp_path, "a.yaml", "tiny", "alpha")
    seed_lessons(lessons, tmp_path)

    write_lesson(tmp_path, "a.yaml", "tiny", "beta")
    seed_lessons(lessons, tmp_path)

    assert lessons.list_ids() == ["tiny"]
    assert lessons.concept_graph() == {"beta": []}


def test_a_bad_file_stops_the_seed_before_anything_is_saved(lessons, tmp_path):
    write_lesson(tmp_path, "a-good.yaml", "good", "alpha")
    (tmp_path / "b-bad.yaml").write_text("id: bad\ntitle: No steps\n", encoding="utf-8")

    with pytest.raises(LessonFileError, match="b-bad.yaml"):
        seed_lessons(lessons, tmp_path)

    assert lessons.list_ids() == []


def test_an_empty_directory_seeds_nothing(lessons, tmp_path):
    assert seed_lessons(lessons, tmp_path) == []
    assert lessons.list_ids() == []
