"""Questions about the learning graph: concepts and what each one requires first."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contract import Mastery
from .models import Progress


def ready_concepts(graph: Mapping[str, Sequence[str]], progress: Progress) -> list[str]:
    """Concepts worth working on next, in the graph's order.

    `graph` maps each concept id to the concept ids it requires. A concept is ready when
    it is not yet solid and everything it requires is: a shaky requirement is a gap to
    close first, not a foundation to build on.
    """
    return [
        concept_id
        for concept_id, requires in graph.items()
        if not _is_solid(progress, concept_id)
        and all(_is_solid(progress, required) for required in requires)
    ]


def mastery_map(progress: Progress, concept_ids: Sequence[str]) -> dict[str, Mastery]:
    """Mastery for every listed concept; a concept the learner has not met is "unseen"."""
    return {concept_id: _mastery(progress, concept_id) for concept_id in concept_ids}


def _mastery(progress: Progress, concept_id: str) -> Mastery:
    concept = progress.concepts.get(concept_id)
    return concept.mastery if concept else "unseen"


def _is_solid(progress: Progress, concept_id: str) -> bool:
    return _mastery(progress, concept_id) == "solid"
