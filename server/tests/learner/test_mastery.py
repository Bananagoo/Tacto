"""How one finished step changes what we know about the learner."""

from tacto.learner.mastery import apply_step_result
from tacto.learner.models import ConceptProgress, Progress

LESSON = "circuits-101"


def test_a_correct_prediction_makes_each_concept_solid():
    after = apply_step_result(Progress(), LESSON, "series", ["current", "series"], True)

    assert after.concepts == {
        "current": ConceptProgress(mastery="solid", correct=1),
        "series": ConceptProgress(mastery="solid", correct=1),
    }


def test_a_wrong_prediction_makes_each_concept_shaky():
    after = apply_step_result(Progress(), LESSON, "series", ["current", "series"], False)

    assert after.concepts == {
        "current": ConceptProgress(mastery="shaky", wrong=1),
        "series": ConceptProgress(mastery="shaky", wrong=1),
    }


def test_a_step_without_a_prediction_raises_unseen_to_shaky_and_counts_nothing():
    after = apply_step_result(Progress(), LESSON, "close_the_loop", ["closed_loop"], None)

    assert after.concepts == {"closed_loop": ConceptProgress(mastery="shaky")}


def test_a_step_without_a_prediction_leaves_known_concepts_alone():
    before = Progress(
        concepts={
            "current": ConceptProgress(mastery="solid", correct=2),
            "series": ConceptProgress(mastery="shaky", wrong=1),
        }
    )

    after = apply_step_result(before, LESSON, "short", ["current", "series"], None)

    assert after.concepts == before.concepts


def test_a_solid_concept_answered_wrong_becomes_shaky():
    before = Progress(concepts={"current": ConceptProgress(mastery="solid", correct=2)})

    after = apply_step_result(before, LESSON, "parallel", ["current"], False)

    assert after.concepts["current"] == ConceptProgress(mastery="shaky", correct=2, wrong=1)


def test_a_shaky_concept_answered_right_becomes_solid():
    before = Progress(concepts={"current": ConceptProgress(mastery="shaky", wrong=1)})

    after = apply_step_result(before, LESSON, "parallel", ["current"], True)

    assert after.concepts["current"] == ConceptProgress(mastery="solid", correct=1, wrong=1)


def test_concepts_the_step_does_not_teach_are_untouched():
    before = Progress(concepts={"voltage": ConceptProgress(mastery="solid", correct=1)})

    after = apply_step_result(before, LESSON, "series", ["current"], False)

    assert after.concepts["voltage"] == ConceptProgress(mastery="solid", correct=1)


def test_the_step_is_recorded_as_completed_in_order():
    first = apply_step_result(Progress(), LESSON, "close_the_loop", ["closed_loop"], None)
    second = apply_step_result(first, LESSON, "series", ["current"], True)

    assert second.completed_steps == {LESSON: ["close_the_loop", "series"]}


def test_a_step_completed_twice_is_listed_once():
    first = apply_step_result(Progress(), LESSON, "series", ["current"], False)
    second = apply_step_result(first, LESSON, "series", ["current"], True)

    assert second.completed_steps == {LESSON: ["series"]}
    assert second.concepts["current"] == ConceptProgress(mastery="solid", correct=1, wrong=1)


def test_steps_are_kept_per_lesson():
    first = apply_step_result(Progress(), LESSON, "series", ["current"], True)
    second = apply_step_result(first, "magnets-101", "series", ["current"], True)

    assert second.completed_steps == {LESSON: ["series"], "magnets-101": ["series"]}


def test_the_progress_passed_in_is_not_mutated():
    before = Progress(
        concepts={"current": ConceptProgress(mastery="solid", correct=1)},
        completed_steps={LESSON: ["close_the_loop"]},
    )
    snapshot = before.model_copy(deep=True)

    after = apply_step_result(before, LESSON, "series", ["current", "series"], False)

    assert before == snapshot
    assert after != before
    # No shared containers either: changing the result later must not reach the original.
    after.completed_steps[LESSON].append("later")
    after.concepts["current"].wrong += 1
    assert before == snapshot
