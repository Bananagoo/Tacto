---
paths:
  - "lessons/**"
  - "server/tacto/lesson.py"
---

# Lesson rules

- A lesson is a fixed list of steps in `lessons/<id>.yaml`. Each step has an `id`, a `prompt` and a `done_when`. The wording belongs to the lesson author; the structure belongs to the vision lane.
- A step completes from the circuit alone. There are no predictions to score, no hints, no timers on the learner and no messages from the browser. A prompt may still ask "what do you expect?" as wording.
- `done_when` is a closed set: `status`, `batteries`, `bulbs`, `lit_bulbs`, `arrangement`. Adding a condition is a code change with a test.
- A step's goal must not already be met by an empty mat or by the circuit that completed the step before it (`test_lesson.py` checks this).
- Physics words are exact: the pulse in the mouse is current, the wheel is voltage.
- Prompts are short enough to read from two metres away: one or two sentences.
