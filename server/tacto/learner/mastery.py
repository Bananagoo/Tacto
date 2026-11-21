"""Update what we know about a learner when they finish a step."""

from __future__ import annotations

from collections.abc import Sequence

from .models import ConceptProgress, Progress


def apply_step_result(
    progress: Progress,
    lesson_id: str,
    step_id: str,
    teaches: Sequence[str],
    correct: bool | None,
) -> Progress:
    """The learner's progress after finishing a step. Returns a new value; the input is untouched.

    `correct` is the step's prediction result, or None when the step asked for none.
    """
    # A deep copy, so the caller can keep comparing against the value it handed in.
    updated = progress.model_copy(deep=True)
    for concept_id in teaches:
        concept = updated.concepts.setdefault(concept_id, ConceptProgress())
        _apply_to_concept(concept, correct)
    completed = updated.completed_steps.setdefault(lesson_id, [])
    if step_id not in completed:
        completed.append(step_id)
    return updated


def _apply_to_concept(concept: ConceptProgress, correct: bool | None) -> None:
    if correct is None:
        # Building the circuit without predicting shows exposure, not understanding:
        # enough to leave "unseen", never enough to change a mastery a prediction earned.
        if concept.mastery == "unseen":
            concept.mastery = "shaky"
    elif correct:
        concept.correct += 1
        concept.mastery = "solid"
    else:
        # The latest prediction decides, so one wrong answer reopens a solid concept.
        concept.wrong += 1
        concept.mastery = "shaky"
