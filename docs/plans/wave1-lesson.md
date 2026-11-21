# Wave 1: lesson and tutor

**Owns:** `lessons/`, `server/tacto/tutor/`, `server/tests/test_tutor_*.py`. Read `.claude/rules/lessons.md` first.

**Goal:** three challenges load from YAML and run through build → predict → test → explain as pure logic, with no network, no audio and no model calls.

## Reuse

- **PyYAML** and **pydantic** (installed): loading and validating lessons.
- Before writing the state machine by hand, run the `reuse-first` skill for "small Python state machine library". Use one only if it is less code than five phases and four transitions written directly; report the result either way. Do not add a dependency yourself.

## Tasks

1. **`tutor/lesson.py`**: pydantic models for the shape in `lessons/circuits-101.yaml` (lesson, challenge, build with `done_when`, predict with choices → keyword lists and the right answer, test, explain, hint ladder) and a loader that validates every file in `lessons/` and fails loudly on a bad one.
2. **`lessons/circuits-101.yaml`**: three challenges, `light_the_bulb`, `series`, `parallel`. Spoken lines are one sentence. Hints step down one at a time and never state the answer. Vibration is current, the wheel is voltage; never mix them. The wording is a draft for the user to edit.
3. **`tutor/match.py`**: transcript or button text → one of the challenge's choices by keyword, or no match. No model call.
4. **`tutor/zone.py`**: the zone rule from the roadmap: running score, +1 for a correct prediction, −1 for a repeated error or 30 s idle, zone changes at ±3 (`too_easy`, `productive`, `stuck`). Time is passed in, never read from the clock inside the rule.
5. **`tutor/learner.py`**: per-concept mastery (`unseen`, `shaky`, `solid`) updated from prediction results, using each challenge's `teaches` list.
6. **`tutor/machine.py`**: the phase machine. Inputs: the circuit summary (status, number of bulbs, series or parallel), `Answer` and `Next` messages, the time. Output: a contract `Tutor` plus the learner map. `build` ends when `done_when` is satisfied; `predict` ends on an answer; `stuck` serves the next hint from the ladder.

## Tests (write first)

- The lesson file loads; a file with a missing answer or an unknown concept is rejected.
- Keyword matching: each choice's keywords match, nonsense does not.
- Zone: three correct in a row → `too_easy`; three repeated errors → `stuck`; idle time counts.
- Machine: one challenge runs through all four phases; a wrong prediction still reaches `explain`; `Next` moves to the next challenge; the last one ends in `done`.
- Hints come out in ladder order and stop at the last one.

## Done when

`make check` passes and a test walks all three challenges end to end.

## Needs a person

The user reviews the lesson wording. The Logitech booth question (does a learning tool qualify) is the user's to ask.
