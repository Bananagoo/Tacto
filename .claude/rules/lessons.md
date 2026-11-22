---
paths:
  - "lessons/**"
  - "server/tacto/lesson.py"
---

# Lesson rules

- A lesson is a fixed list of steps in `lessons/<id>.yaml`. Each step has an `id`, a `prompt` and a `done_when`. The wording belongs to the lesson author; the structure belongs to the vision lane.
- A step completes from the circuit and the fingertip alone. There are no predictions to score and no hints. The one exception is a step's `reflection` (docs/voice-reflections-plan.md): the learner answers out loud or types, an answer grader gives a label, and code moves through prewritten questions; Continue or Skip moves on.
- `done_when` is a closed set: `status`, `batteries`, `bulbs`, `lit_bulbs`, `arrangement`, `switch_closed`, `min_voltage`, `max_voltage`, `touching` (see `lessons/README.md`). Adding a condition is a code change with a test.
- A step's goal must not already be met by an empty mat or by the circuit that completed the step before it (`test_lesson.py` and `test_short_lesson.py` check this).
- The lab runs `circuits-101.yaml` (the short demo); `circuits-101-full.yaml` is the six-step reference.
- Physics words are exact: the pulse in the mouse is current, the wheel is voltage.
- Prompts are short enough to read from two metres away: one or two sentences.
