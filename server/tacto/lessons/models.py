"""What a lesson is. Lessons are data: a second lesson is a new file, not new code.

Each step runs in a fixed order:

    predict (optional) -> build -> test -> explain

The learner predicts what a change will do, makes the change on the mat, feels and
sees the result, and only then hears the explanation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contract import CircuitStatus, Topology


class _Strict(BaseModel):
    # A typo in a lesson file should fail loudly at load time, not be ignored.
    model_config = ConfigDict(extra="forbid")


class DoneWhen(_Strict):
    """Conditions on the solved circuit. Every condition given must hold."""

    status: CircuitStatus | None = None
    bulbs: int | None = Field(None, ge=0)  # bulbs on the mat
    lit_bulbs: int | None = Field(None, ge=0)  # bulbs carrying current
    topology: Topology | None = None

    @model_validator(mode="after")
    def _has_a_condition(self) -> DoneWhen:
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("done_when needs at least one condition")
        return self


class Build(_Strict):
    say: str
    done_when: DoneWhen


class Predict(_Strict):
    say: str
    # choice shown on screen -> words that count as that choice when spoken
    choices: dict[str, list[str]] = Field(min_length=2, max_length=4)
    answer: str
    # wrong choice -> what the tutor says about that idea, after the test
    misconceptions: dict[str, str] = {}

    @model_validator(mode="after")
    def _choices_are_consistent(self) -> Predict:
        if self.answer not in self.choices:
            raise ValueError(f"answer {self.answer!r} is not one of the choices")
        for choice in self.misconceptions:
            if choice not in self.choices:
                raise ValueError(f"misconception {choice!r} is not one of the choices")
            if choice == self.answer:
                raise ValueError("the right answer cannot be a misconception")
        return self


class Observe(_Strict):
    say: str


class Explain(_Strict):
    say: str


class Step(_Strict):
    id: str
    teaches: list[str] = Field(min_length=1)  # concept ids
    predict: Predict | None = None
    build: Build
    observe: Observe
    explain: Explain
    hints: list[str] = []  # a ladder: each one a step smaller, none states the answer


class ConceptDef(_Strict):
    id: str
    title: str
    requires: list[str] = []  # concept ids that should come first


class Lesson(_Strict):
    id: str
    title: str
    language: str = "en"
    concepts: list[ConceptDef] = Field(min_length=1)
    steps: list[Step] = Field(min_length=1)

    @model_validator(mode="after")
    def _references_resolve(self) -> Lesson:
        concept_ids = [concept.id for concept in self.concepts]
        if len(set(concept_ids)) != len(concept_ids):
            raise ValueError("concept ids must be unique")
        step_ids = [step.id for step in self.steps]
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("step ids must be unique")
        known = set(concept_ids)
        for concept in self.concepts:
            unknown = set(concept.requires) - known
            if unknown:
                raise ValueError(f"concept {concept.id!r} requires unknown {sorted(unknown)}")
        for step in self.steps:
            unknown = set(step.teaches) - known
            if unknown:
                raise ValueError(f"step {step.id!r} teaches unknown {sorted(unknown)}")
        return self
