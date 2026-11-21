"""Lesson files are written by hand, so every way one can be wrong must name the file."""

from pathlib import Path

import pytest

from tacto.lessons.loader import LessonFileError, load_lesson, load_lessons

MINIMAL_LESSON = """\
id: {lesson_id}
title: A tiny lesson
concepts:
  - id: closed_loop
    title: Closed loop
steps:
  - id: only_step
    teaches: [closed_loop]
    build:
      say: Close the loop.
      done_when: {{ status: closed }}
    observe:
      say: Touch a wire.
    explain:
      say: Current needs a closed loop.
"""


def write_lesson(directory: Path, file_name: str, lesson_id: str) -> Path:
    path = directory / file_name
    path.write_text(MINIMAL_LESSON.format(lesson_id=lesson_id), encoding="utf-8")
    return path


def test_a_valid_file_becomes_a_lesson(tmp_path):
    lesson = load_lesson(write_lesson(tmp_path, "tiny.yaml", "tiny"))

    assert lesson.id == "tiny"
    assert [step.id for step in lesson.steps] == ["only_step"]


def test_a_missing_file_is_reported_by_name(tmp_path):
    with pytest.raises(LessonFileError, match="nowhere.yaml"):
        load_lesson(tmp_path / "nowhere.yaml")


def test_a_file_that_is_not_yaml_is_reported_by_name(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("id: [unclosed\n", encoding="utf-8")

    with pytest.raises(LessonFileError, match="broken.yaml"):
        load_lesson(path)


@pytest.mark.parametrize("text", ["- just\n- a list\n", "only a sentence\n", ""])
def test_a_file_whose_top_level_is_not_a_mapping_is_reported_by_name(tmp_path, text):
    path = tmp_path / "shapeless.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(LessonFileError, match="shapeless.yaml.*mapping"):
        load_lesson(path)


def test_a_file_that_fails_validation_says_which_file_and_which_field(tmp_path):
    path = tmp_path / "typo.yaml"
    path.write_text(
        MINIMAL_LESSON.format(lesson_id="typo").replace("observe:", "obzerve:"),
        encoding="utf-8",
    )

    with pytest.raises(LessonFileError) as raised:
        load_lesson(path)

    assert "typo.yaml" in str(raised.value)
    assert "obzerve" in str(raised.value)


def test_a_lesson_file_error_is_a_value_error():
    assert issubclass(LessonFileError, ValueError)


def test_lessons_come_back_sorted_by_file_name(tmp_path):
    write_lesson(tmp_path, "b-second.yaml", "second")
    write_lesson(tmp_path, "a-first.yaml", "first")
    write_lesson(tmp_path, "c-third.yaml", "third")

    assert [lesson.id for lesson in load_lessons(tmp_path)] == ["first", "second", "third"]


def test_files_that_are_not_lessons_are_ignored(tmp_path):
    write_lesson(tmp_path, "tiny.yaml", "tiny")
    (tmp_path / "README.md").write_text("# Lessons\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not: a lesson\n", encoding="utf-8")

    assert [lesson.id for lesson in load_lessons(tmp_path)] == ["tiny"]


def test_two_files_with_the_same_lesson_id_are_rejected(tmp_path):
    write_lesson(tmp_path, "one.yaml", "twin")
    write_lesson(tmp_path, "two.yaml", "twin")

    with pytest.raises(LessonFileError, match="two.yaml.*twin.*one.yaml"):
        load_lessons(tmp_path)


def test_the_lessons_shipped_in_the_repository_load():
    lessons_directory = Path(__file__).resolve().parents[3] / "lessons"

    lessons = {lesson.id: lesson for lesson in load_lessons(lessons_directory)}

    assert [step.id for step in lessons["circuits-101"].steps] == [
        "setup",
        "close_the_loop",
        "series",
        "parallel",
        "short",
    ]
