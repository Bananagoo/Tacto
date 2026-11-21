---
paths:
  - "lessons/**"
  - "server/tacto/tutor/**"
  - "web/src/voice/**"
---

# Lesson and tutor rules

The learner is someone who has never seen a circuit. Scholé judges whether it teaches, not whether it is polished.

- Every challenge follows build → predict → test → explain. The explanation comes only after the learner has seen their prediction succeed or fail.
- Predictions are a closed set of two to four spoken choices ("brighter", "dimmer", "the same"). Match keywords first; call a model only when no keyword matches.
- Hints form a ladder: a smaller question, then a pointer to where to look or touch, then a worked example on the learner's own circuit. One step per request. No step states the answer to the prediction.
- Tutor lines are spoken: one sentence, under 20 words, no symbols or units that read badly aloud, second person, no praise inflation.
- Vibration is current. The wheel is voltage. Check every line for this before committing; it is the misconception the lesson exists to fix.
- Zone rule: score +1 for a correct prediction, −1 for a repeated error or 30 s with no hand activity; change zone at ±3. Too easy → skip ahead or remove guidance. Productive → stay quiet. Stuck → one step down the ladder.
- Signals come from the desk only: predictions, circuit edits, hand activity, idle time. No emotion inference, nothing recorded.
- Lesson content lives in YAML in `lessons/` and is validated by a pydantic model at startup. Changing wording must not require changing code.
- Scripted lines are pre-generated to audio and committed, so the demo does not depend on Wi-Fi.
