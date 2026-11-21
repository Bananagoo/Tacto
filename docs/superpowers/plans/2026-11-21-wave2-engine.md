# Wave 2, lesson engine and learner model lane: implementation plan

> Read `2026-11-21-wave2-README.md` first: it lists what is frozen and the constraints every lane shares.

**Goal:** the logic that walks a learner through any lesson, step by step, and keeps track of how they are doing.

**Architecture:** a pure state machine. It is given a `Lesson` and a learner's `Progress`, fed events (the solved circuit, an answer, "next", the time), and asked for the `Tutor` to show. It never reads a clock, a file, the network or a database: time is passed in and results come out as events for someone else to save.

**Tech stack:** pydantic, the standard library. Before writing the phase machine by hand, check whether a small state-machine library would be less code than five phases and four transitions written directly; report what you found either way, and do not add a dependency yourself.

## Files

| File | Responsibility |
|---|---|
| `server/tacto/lessons/conditions.py` | Does a solved circuit satisfy a step's `done_when`? |
| `server/tacto/lessons/matching.py` | Spoken or clicked text → one of a prediction's choices |
| `server/tacto/lessons/events.py` | The events the engine emits |
| `server/tacto/lessons/engine.py` | `LessonEngine`, the phase machine |
| `server/tacto/learner/mastery.py` | Update concept mastery from a step's result |
| `server/tacto/learner/zone.py` | The zone rule |
| `server/tacto/learner/graph.py` | Questions about the learning graph |
| `server/tests/lessons/test_*.py`, `server/tests/learner/test_*.py` | Tests |

## Interfaces you produce

```python
# tacto/lessons/conditions.py
def is_satisfied(done_when: DoneWhen, circuit: Circuit) -> bool: ...

# tacto/lessons/matching.py
def match_choice(text: str, choices: dict[str, list[str]]) -> str | None: ...

# tacto/lessons/events.py
class PredictionMade(BaseModel):  step_id: str; choice: str; correct: bool; at: datetime
class StepCompleted(BaseModel):   step_id: str; teaches: list[str]; correct: bool | None; at: datetime
class LessonCompleted(BaseModel): lesson_id: str; at: datetime
LessonEvent = PredictionMade | StepCompleted | LessonCompleted

# tacto/lessons/engine.py
class LessonEngine:
    def __init__(self, lesson: Lesson, progress: Progress, *, now: datetime) -> None: ...
    def on_circuit(self, circuit: Circuit, *, now: datetime) -> None: ...
    def on_answer(self, text: str, *, now: datetime) -> None: ...
    def on_next(self, *, now: datetime) -> None: ...
    def on_tick(self, *, now: datetime) -> None: ...
    def tutor(self) -> Tutor: ...
    def drain_events(self) -> list[LessonEvent]: ...   # returns and clears what happened since last call
    @property
    def progress(self) -> Progress: ...                # updated as steps complete

# tacto/learner/mastery.py
def apply_step_result(progress: Progress, lesson_id: str, step_id: str,
                      teaches: Sequence[str], correct: bool | None) -> Progress: ...

# tacto/learner/zone.py
class ZoneTracker:
    def record_correct(self) -> None: ...
    def record_repeated_error(self) -> None: ...
    def record_idle(self) -> None: ...
    @property
    def score(self) -> int: ...
    @property
    def zone(self) -> Zone: ...

# tacto/learner/graph.py
def ready_concepts(graph: Mapping[str, Sequence[str]], progress: Progress) -> list[str]: ...
def mastery_map(progress: Progress, concept_ids: Sequence[str]) -> dict[str, Mastery]: ...
```

`Lesson`, `Step`, `DoneWhen`, `Predict` are in `tacto/lessons/models.py`; `Progress`, `ConceptProgress` in `tacto/learner/models.py`; `Circuit`, `Tutor`, `Zone`, `Mastery`, `Phase` in `tacto/contract.py`. All frozen: read them first.

## Behaviour

**Phases.** Each step runs `predict` (only if the step has one) → `build` → `test` → `explain`, then the next step; after the last step the phase is `done`.

| Phase | `Tutor.prompt` | Leaves when |
|---|---|---|
| `predict` | `predict.say`; `choices` are the choice names in file order | `on_answer` matches a choice |
| `build` | `build.say` | `on_circuit` satisfies `done_when` |
| `test` | `observe.say` | `on_next` |
| `explain` | `explain.say`; `feedback` is the misconception line for the learner's wrong choice, if the step has one | `on_next` |
| `done` | The last step's `explain.say` | never |

- Events in the wrong phase are ignored: an answer outside `predict`, `on_next` in `predict` or `build`.
- An answer that matches no choice changes nothing.
- A step whose `done_when` already holds when its `build` phase starts moves on at the next `on_circuit`, not instantly: the learner must see the build line.
- `Tutor` always carries `lesson_id`, `challenge_id` (the step id), `step_index`, `step_count`, `zone` and `score`. `correct` is `None` until the step's prediction is answered and resets on the next step. `choices` is empty outside `predict`. `audio_url` stays `None`.
- Starting position: the first step not in `progress.completed_steps[lesson.id]`. If every step is complete, start at `done`.

**Events.** `PredictionMade` when an answer is accepted. `StepCompleted` when a step's `explain` phase is left. `LessonCompleted` after the last step. `progress` is updated with `apply_step_result` at the same moment as `StepCompleted`.

**Conditions.** `status` and `topology` compare with the circuit's. `bulbs` counts parts of kind `bulb`. `lit_bulbs` counts bulbs whose `brightness` is above `LIT_THRESHOLD = 0.02`. Conditions that are `None` are not checked.

**Matching.** Case-insensitive, punctuation ignored. An exact match on a choice name wins. Otherwise a choice matches if the text contains one of its keywords as a whole word or phrase. If more than one choice matches, return `None`: an ambiguous answer is not an answer.

**Mastery.** For each concept the step teaches: a correct prediction adds one to `correct` and makes it `solid`; a wrong one adds one to `wrong` and makes it `shaky`; a step with no prediction (`correct is None`) raises `unseen` to `shaky` and changes nothing else. A `solid` concept answered wrong later becomes `shaky`. The step id is appended to `completed_steps[lesson_id]` once. Return a new `Progress`; do not mutate the argument.

**Zone.** Score starts at 0: +1 for a correct prediction, −1 for a repeated error, −1 for an idle period. `too_easy` at +3 or more, `stuck` at −3 or less, otherwise `productive`.

**Hints and idle time.** In `build`, each `IDLE_SECONDS = 30.0` that pass (measured through `on_tick`'s `now`) with no change to the circuit reveals the next hint and records one idle period. `Tutor.hint` holds the current hint, one at a time in ladder order, and stops at the last. A circuit change (compare the parts' and wires' positions, not their currents) restarts the timer. Hints clear when the step's `build` phase ends. A wrong prediction on a concept the learner already has a `wrong` count for is a repeated error.

**Learning graph.** `ready_concepts` returns, in the graph's order, the concepts that are not `solid` and whose requirements are all `solid`. `mastery_map` gives every listed concept its mastery, `unseen` when absent.

## Tasks

Each task: write the tests, watch them fail, implement, watch them pass, commit.

1. **Conditions.** Tests: each condition alone, all together, an unmet one among met ones, a dim bulb under the threshold is not lit.
2. **Matching.** Tests: exact name; keyword inside a sentence ("I think it gets dimmer"); case and punctuation; a keyword must be a whole word ("no" does not match "know"); two choices matching is `None`; empty text is `None`.
3. **Mastery.** Tests: every rule above; the input is not mutated; a step completed twice is listed once.
4. **Zone.** Tests: three correct → `too_easy`; three repeated errors → `stuck`; mixed stays `productive`; the boundaries at exactly ±3.
5. **Learning graph.** Tests with the six-concept graph from the spec: a new learner is ready for `closed_loop` only; with `closed_loop` solid, `current` and `voltage`; a concept is never ready while a requirement is shaky.
6. **Engine.** Build a small two-step lesson in the tests (one step with a prediction and one without) plus `Circuit` values that do and do not satisfy each `done_when`. Tests: a full walk through both steps with the `Tutor` checked at every phase; the emitted events in order with the times passed in; a wrong answer still reaches `explain` and shows the misconception line; ignored events in each phase; resuming from `Progress` with the first step complete; resuming a finished lesson is `done`; hints appear at 30 s and 60 s of no change, stop after the last, and clear when the circuit satisfies the step; a circuit change restarts the idle timer; `drain_events` clears.

## Review focus

- Time never comes from the clock inside these modules: every test must be repeatable to the microsecond.
- Feeding `on_circuit` fifteen times a second with the same circuit must be cheap and must not emit anything.
- A lesson with a single step, and a step with no hints, must work.
- An answer arriving twice (voice and button together) must count once.
- `progress` handed to the engine must not be mutated behind the caller's back.

## Needs a person

Nothing on hardware. The 30 s idle time and the mastery rules are product choices for the project owner to confirm.
