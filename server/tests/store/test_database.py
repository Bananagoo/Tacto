"""The database file is created on demand and survives being opened again."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect
from store_samples import make_lesson

from tacto.store.db import DEFAULT_DATABASE_URL, create_database
from tacto.store.lessons import SqlLessonRepository
from tacto.store.tables import UtcDateTime

EXPECTED_TABLES = {
    "lesson",
    "lesson_step",
    "concept",
    "concept_prerequisite",
    "learner",
    "mastery",
    "completed_step",
    "attempt",
}


def test_the_default_database_lives_in_the_ignored_data_directory():
    assert DEFAULT_DATABASE_URL == "sqlite:///data/tacto.db"


def test_creating_the_database_creates_every_table(engine):
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_the_directory_for_the_database_file_is_created(tmp_path):
    path = tmp_path / "not" / "there" / "yet" / "tacto.db"

    create_database(f"sqlite:///{path}").dispose()

    assert path.is_file()


def test_opening_an_existing_database_keeps_its_data(tmp_path):
    url = f"sqlite:///{tmp_path / 'tacto.db'}"
    first = create_database(url)
    SqlLessonRepository(first).save(make_lesson())
    first.dispose()

    # A later run of the server, with the same schema, opens the same file.
    second = create_database(url)

    assert SqlLessonRepository(second).get("circuits-101") == make_lesson()
    second.dispose()


def test_one_in_memory_database_is_shared_by_every_thread(engine):
    # The server answers requests on worker threads; they must all see the same data.
    SqlLessonRepository(engine).save(make_lesson())

    with ThreadPoolExecutor(max_workers=1) as pool:
        seen = pool.submit(SqlLessonRepository(engine).list_ids).result()

    assert seen == ["circuits-101"]


def test_a_stored_time_is_utc_without_a_zone_and_comes_back_as_aware_utc(engine):
    column = UtcDateTime()
    half_past_one_in_paris = datetime(2026, 11, 21, 13, 30, tzinfo=timezone(timedelta(hours=1)))

    stored = column.process_bind_param(half_past_one_in_paris, engine.dialect)
    loaded = column.process_result_value(stored, engine.dialect)

    assert stored == datetime(2026, 11, 21, 12, 30)
    assert loaded == half_past_one_in_paris
    assert loaded.tzinfo is UTC


def test_a_time_without_a_zone_never_reaches_the_database(engine):
    with pytest.raises(ValueError, match="zone"):
        UtcDateTime().process_bind_param(datetime(2026, 11, 21, 12, 30), engine.dialect)
