"""Questions about the learning graph: what is the learner ready for, and where do they stand?"""

from tacto.contract import Mastery
from tacto.learner.graph import mastery_map, ready_concepts
from tacto.learner.models import ConceptProgress, Progress

# The six concepts of Circuits 101: concept -> what should come first.
GRAPH = {
    "closed_loop": [],
    "current": ["closed_loop"],
    "voltage": ["closed_loop"],
    "resistance": ["current", "voltage"],
    "series": ["current", "resistance"],
    "parallel": ["series"],
}


def progress(**masteries: Mastery) -> Progress:
    return Progress(
        concepts={concept: ConceptProgress(mastery=m) for concept, m in masteries.items()}
    )


def test_a_new_learner_is_ready_for_the_root_only():
    assert ready_concepts(GRAPH, Progress()) == ["closed_loop"]


def test_a_solid_requirement_opens_what_depends_on_it():
    assert ready_concepts(GRAPH, progress(closed_loop="solid")) == ["current", "voltage"]


def test_a_concept_is_not_ready_while_a_requirement_is_shaky():
    standing = progress(closed_loop="solid", current="solid", voltage="shaky")

    ready = ready_concepts(GRAPH, standing)

    assert "resistance" not in ready  # needs voltage, which is only shaky
    assert ready == ["voltage"]


def test_a_shaky_concept_with_solid_requirements_is_still_ready():
    assert ready_concepts(GRAPH, progress(closed_loop="shaky")) == ["closed_loop"]


def test_solid_concepts_are_not_offered_again():
    standing = progress(closed_loop="solid", current="solid", voltage="solid")

    assert ready_concepts(GRAPH, standing) == ["resistance"]


def test_every_requirement_must_be_solid():
    standing = progress(closed_loop="solid", current="solid", voltage="solid", resistance="shaky")

    assert ready_concepts(GRAPH, standing) == ["resistance"]  # series also needs resistance


def test_ready_concepts_come_in_the_graphs_order():
    reordered = {"voltage": ["closed_loop"], "current": ["closed_loop"], "closed_loop": []}

    assert ready_concepts(reordered, progress(closed_loop="solid")) == ["voltage", "current"]


def test_nothing_is_ready_when_everything_is_solid():
    standing = progress(**dict.fromkeys(GRAPH, "solid"))

    assert ready_concepts(GRAPH, standing) == []


def test_the_mastery_map_lists_every_concept_asked_for():
    standing = progress(closed_loop="solid", current="shaky")

    assert mastery_map(standing, list(GRAPH)) == {
        "closed_loop": "solid",
        "current": "shaky",
        "voltage": "unseen",
        "resistance": "unseen",
        "series": "unseen",
        "parallel": "unseen",
    }


def test_the_mastery_map_leaves_out_concepts_not_asked_for():
    standing = progress(closed_loop="solid", magnetism="solid")

    assert mastery_map(standing, ["closed_loop"]) == {"closed_loop": "solid"}
