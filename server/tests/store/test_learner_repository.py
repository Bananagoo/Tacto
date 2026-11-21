"""Learners, their progress and their predictions. A nickname is all we keep about a person."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from tacto.learner.models import Attempt, ConceptProgress, Progress
from tacto.store.learners import SqlLearnerRepository
from tacto.store.repositories import LearnerRepository
from tacto.store.tables import AttemptRow, CompletedStepRow, LearnerRow, MasteryRow

UNUSUAL_NICKNAMES = [
    "O'Brien",
    'Dwayne "The Rock"',
    "Robert'); DROP TABLE learner;--",
    "100% \\ real_name",
    "🦊 fox 🔥",
    "Zoë Åström",
    "名前",
    "x" * 5000,
]


@pytest.fixture
def learners(engine) -> SqlLearnerRepository:
    return SqlLearnerRepository(engine)


def attempt(step_id: str, at: datetime, correct: bool = True) -> Attempt:
    return Attempt(
        lesson_id="circuits-101", step_id=step_id, choice="dimmer", correct=correct, at=at
    )


def count(engine, table: type) -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(table)).one()


def stored_nickname(engine, learner_id: int) -> str:
    with Session(engine) as session:
        return session.get(LearnerRow, learner_id).nickname


def test_it_satisfies_the_repository_interface(learners):
    repository: LearnerRepository = learners  # checked by the type checker, documented here
    assert repository.attempts(repository.get_or_create("Ada")) == []


# --- who the learner is ---


def test_the_same_nickname_is_the_same_learner(learners):
    assert learners.get_or_create("Ada") == learners.get_or_create("Ada")


def test_different_nicknames_are_different_learners(learners):
    assert learners.get_or_create("Ada") != learners.get_or_create("Grace")


@pytest.mark.parametrize("typed", ["  Ada  ", "ada", "ADA", "\tAdA\n"])
def test_spaces_around_a_nickname_and_its_case_do_not_matter(learners, typed):
    assert learners.get_or_create(typed) == learners.get_or_create("Ada")


def test_case_is_ignored_beyond_plain_letters(learners):
    assert learners.get_or_create("ZOË") == learners.get_or_create("zoë")
    # The same name typed with a combining accent is still the same name.
    assert learners.get_or_create("zoë") == learners.get_or_create("zoë")


@pytest.mark.parametrize("nickname", ["", "   ", "\t\n"])
def test_an_empty_nickname_is_rejected(engine, learners, nickname):
    with pytest.raises(ValueError, match="nickname"):
        learners.get_or_create(nickname)

    assert count(engine, LearnerRow) == 0


@pytest.mark.parametrize("nickname", UNUSUAL_NICKNAMES)
def test_an_unusual_nickname_is_stored_exactly_and_found_again(engine, learners, nickname):
    learner_id = learners.get_or_create(nickname)

    assert stored_nickname(engine, learner_id) == nickname
    assert learners.get_or_create(nickname) == learner_id
    assert count(engine, LearnerRow) == 1


def test_the_nickname_is_kept_as_first_typed(engine, learners):
    learner_id = learners.get_or_create("  Ada Lovelace ")
    learners.get_or_create("ADA LOVELACE")

    assert stored_nickname(engine, learner_id) == "Ada Lovelace"


def test_a_new_learner_is_given_a_creation_time_with_a_zone(engine, learners):
    before = datetime.now(UTC)
    learner_id = learners.get_or_create("Ada")

    with Session(engine) as session:
        created_at = session.get(LearnerRow, learner_id).created_at

    assert created_at.tzinfo is not None
    assert before <= created_at <= datetime.now(UTC)


# --- progress ---


def test_a_new_learner_has_empty_progress(learners):
    assert learners.load_progress(learners.get_or_create("Ada")) == Progress()


def test_saved_progress_loads_back_equal(learners):
    learner_id = learners.get_or_create("Ada")
    progress = Progress(
        concepts={
            "closed_loop": ConceptProgress(mastery="solid", correct=3, wrong=0),
            "current": ConceptProgress(mastery="shaky", correct=1, wrong=2),
            "voltage": ConceptProgress(),
        },
        # Deliberately not alphabetical: the order finished is what must come back.
        completed_steps={
            "circuits-101": ["setup", "series", "close_the_loop"],
            "another-lesson": ["zulu", "alpha"],
        },
    )

    learners.save_progress(learner_id, progress)
    loaded = learners.load_progress(learner_id)

    assert loaded == progress
    assert loaded.completed_steps["circuits-101"] == ["setup", "series", "close_the_loop"]
    assert loaded.completed_steps["another-lesson"] == ["zulu", "alpha"]


def test_saving_progress_twice_does_not_duplicate_rows(engine, learners):
    learner_id = learners.get_or_create("Ada")
    progress = Progress(
        concepts={"current": ConceptProgress(mastery="shaky", correct=1, wrong=1)},
        completed_steps={"circuits-101": ["setup", "close_the_loop"]},
    )

    learners.save_progress(learner_id, progress)
    learners.save_progress(learner_id, progress)

    assert count(engine, MasteryRow) == 1
    assert count(engine, CompletedStepRow) == 2
    assert learners.load_progress(learner_id) == progress


def test_saving_progress_replaces_what_was_there(learners):
    learner_id = learners.get_or_create("Ada")
    learners.save_progress(
        learner_id,
        Progress(
            concepts={"current": ConceptProgress(mastery="shaky", correct=1, wrong=1)},
            completed_steps={"circuits-101": ["setup"]},
        ),
    )
    later = Progress(
        concepts={"voltage": ConceptProgress(mastery="solid", correct=4, wrong=1)},
        completed_steps={"circuits-101": ["close_the_loop", "setup"]},
    )

    learners.save_progress(learner_id, later)

    assert learners.load_progress(learner_id) == later


def test_progress_of_two_learners_does_not_mix(learners):
    ada, grace = learners.get_or_create("Ada"), learners.get_or_create("Grace")
    ada_progress = Progress(
        concepts={"current": ConceptProgress(mastery="solid", correct=5, wrong=0)},
        completed_steps={"circuits-101": ["setup", "close_the_loop"]},
    )
    grace_progress = Progress(
        concepts={"current": ConceptProgress(mastery="shaky", correct=0, wrong=2)},
        completed_steps={"circuits-101": ["setup"]},
    )

    learners.save_progress(ada, ada_progress)
    learners.save_progress(grace, grace_progress)
    learners.save_progress(ada, ada_progress)

    assert learners.load_progress(ada) == ada_progress
    assert learners.load_progress(grace) == grace_progress


def test_progress_cannot_be_saved_for_a_learner_who_does_not_exist(engine, learners):
    with pytest.raises(IntegrityError):
        learners.save_progress(
            999, Progress(concepts={"current": ConceptProgress(mastery="shaky")})
        )

    assert count(engine, MasteryRow) == 0


# --- prediction attempts ---


def test_attempts_come_back_oldest_first(learners):
    learner_id = learners.get_or_create("Ada")
    noon = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    # Recorded out of order, as could happen if a write is retried.
    learners.record_attempt(learner_id, attempt("series", noon + timedelta(minutes=5)))
    learners.record_attempt(learner_id, attempt("close_the_loop", noon, correct=False))
    learners.record_attempt(learner_id, attempt("parallel", noon + timedelta(minutes=9)))

    assert [found.step_id for found in learners.attempts(learner_id)] == [
        "close_the_loop",
        "series",
        "parallel",
    ]


def test_attempts_at_the_same_moment_keep_the_order_they_were_recorded(learners):
    learner_id = learners.get_or_create("Ada")
    noon = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    for step_id in ("first", "second", "third"):
        learners.record_attempt(learner_id, attempt(step_id, noon))

    assert [found.step_id for found in learners.attempts(learner_id)] == [
        "first",
        "second",
        "third",
    ]


def test_an_attempt_reads_back_equal(learners):
    learner_id = learners.get_or_create("Ada")
    recorded = Attempt(
        lesson_id="circuits-101",
        step_id="series",
        choice="first brighter",
        correct=False,
        at=datetime(2026, 11, 21, 12, 0, 0, 123456, tzinfo=UTC),
    )

    learners.record_attempt(learner_id, recorded)

    assert learners.attempts(learner_id) == [recorded]


@pytest.mark.parametrize("hours", [-8, 0, 1, 5.5, 13])
def test_a_time_keeps_its_moment_whatever_zone_it_was_recorded_in(learners, hours):
    learner_id = learners.get_or_create("Ada")
    zone = timezone(timedelta(hours=hours))
    # 23:30 local: in most of these zones the UTC date differs from the local date.
    local = datetime(2026, 11, 21, 23, 30, tzinfo=zone)

    learners.record_attempt(learner_id, attempt("series", local))
    (found,) = learners.attempts(learner_id)

    assert found.at.tzinfo is not None
    assert found.at.utcoffset() == timedelta(0)
    assert found.at == local
    assert found.at.timestamp() == local.timestamp()


def test_attempts_in_different_zones_are_ordered_by_moment_not_by_clock_reading(learners):
    learner_id = learners.get_or_create("Ada")
    tokyo = timezone(timedelta(hours=9))
    # 20:00 in Tokyo is 11:00 UTC: earlier than 12:00 UTC although the clock reads later.
    learners.record_attempt(learner_id, attempt("utc", datetime(2026, 11, 21, 12, tzinfo=UTC)))
    learners.record_attempt(learner_id, attempt("tokyo", datetime(2026, 11, 21, 20, tzinfo=tokyo)))

    assert [found.step_id for found in learners.attempts(learner_id)] == ["tokyo", "utc"]


def test_a_time_without_a_zone_is_rejected(engine, learners):
    learner_id = learners.get_or_create("Ada")

    with pytest.raises(ValueError, match="zone"):
        learners.record_attempt(learner_id, attempt("series", datetime(2026, 11, 21, 12, 0)))

    assert count(engine, AttemptRow) == 0


def test_attempts_of_two_learners_do_not_mix(learners):
    ada, grace = learners.get_or_create("Ada"), learners.get_or_create("Grace")
    noon = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)

    learners.record_attempt(ada, attempt("series", noon))
    learners.record_attempt(grace, attempt("parallel", noon))

    assert [found.step_id for found in learners.attempts(ada)] == ["series"]
    assert [found.step_id for found in learners.attempts(grace)] == ["parallel"]


def test_an_attempt_cannot_be_recorded_for_a_learner_who_does_not_exist(engine, learners):
    with pytest.raises(IntegrityError):
        learners.record_attempt(999, attempt("series", datetime(2026, 11, 21, 12, tzinfo=UTC)))

    assert count(engine, AttemptRow) == 0
