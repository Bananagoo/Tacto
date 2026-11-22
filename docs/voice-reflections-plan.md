# Plan: adaptive voice reflections for the Tacto lab

Given by Katie on 22 Nov 2026. Built in phases, in order; each phase has a check.
Progress and the decisions made along the way are at the bottom.

## Goal

Three of the six lesson steps end in a reflection question. Make it a spoken exchange: the lab asks the question aloud, the student answers by voice, a classifier grades the answer, and the lab either moves on or asks one or two narrower questions until the idea lands.

The six steps, their completion conditions and the 6 s auto-advance on steps 1 to 3 stay exactly as they are. This work only changes what happens after steps 4, 5 and 6 complete.

## Rules

1. Audit first, and report where the plan does not fit the repo.
2. The model grades; code decides. The language model returns a label from a fixed set. It never chooses the next question, never writes tutor lines, and never advances a step.
3. Every tutor line is prewritten in the lesson YAML. No generated speech text.
4. All model calls go through Together AI, from the Python server only. Key in `TOGETHER_API_KEY`, read from the environment, never sent to the browser or committed.
5. Do not trust model IDs from memory. List the account's models and read the current docs, then record the chosen IDs in one config file.
6. Voice is a layer, not a dependency. Behind a `VOICE_ENABLED` flag. With it off, or with the network down, the six steps run as they do today.
7. Fail towards more help. Any error, timeout or unreadable answer is treated as "partial", which moves one level down the funnel.
8. Reuse before build. No agent framework, no database.
9. The state message is a contract with the UI lane. Add fields; do not rename or remove any.

## The funnel

| Level | Type | Resolved by |
|---|---|---|
| 0 | Open "why" question | Speech |
| 1 | Focusing question: points at the feature that matters | Speech |
| 2 | Forced choice between two options | Speech |
| Exit | Lab states the idea, then asks for an action on the mat | Circuit state |

- `correct` at any level: speak the confirmation, go to the next step.
- `partial` or `incorrect`: go down one level. After level 2, go to the exit.
- `unclear` (empty, off topic, too short to grade): repeat the same question once, without using a level. A second `unclear` counts as `partial`.
- Exit: complete when the circuit state meets the exit condition, or after 20 s.

A reflection asks at most three graded questions and cannot loop. The wording of every question, confirmation and exit line is in `lessons/circuits-101.yaml`.

## Phases

| # | Phase | Check |
|---|---|---|
| 0 | Audit and smoke test (`scripts/together_smoke.py`), models chosen | The script passes three times in a row; model IDs are in config |
| 1 | Lesson schema: a reflection can hold a funnel | Lessons load at startup; a malformed funnel fails validation with a readable message |
| 2 | Funnel state machine, a pure module with no I/O | Unit tests for every transition, including two unclear in a row, exit by circuit state and exit by timeout |
| 3 | Classifier: transcript, question, rubric, circuit summary in; `{label, misconception, ideas_matched}` out. JSON schema, temperature 0, 4 s timeout then `partial` | At least 90% of fixtures get the expected label, and no incorrect fixture is ever labelled correct |
| 4 | End to end in text: wired into the lesson runner, new state fields, a typed-answer event and text box | All three reflections can be driven by typed answers through every path; with `VOICE_ENABLED` off, behaviour matches today's |
| 5 | Speech out: every tutor line synthesised at startup and cached on disk | A second startup makes zero text-to-speech calls; with the network off, cached lines still play |
| 6 | Speech in: browser voice detection, half duplex, clip to server, transcript on screen | Ten spoken answers in a row are transcribed and graded; end of speech to next line is measured |
| 7 | Fail-safes and ledger: repeat then text box, push-to-talk, visible listening and thinking states, one record per answer | Kill the network mid-reflection; the session reaches the next step without a restart |

## Decisions made while building

- Text-to-speech, LLM grading and spoken tutor lines were on the parked list; Katie un-parked them on 22 Nov ("make the necessary fixes and unblocking to keep going").
- Step 4's exit is "down to 3 V, then back up to 6 V", not "3 V or less", so every learner does steps 5 and 6 at the same current.
- A funnel shares its target idea, confirmation and misconceptions across its levels; each level has its own question and example answers.
- A reflection in the lesson file may still be a single question, which behaves as before.
- The 90% fixture check in phase 3 is a script run on demand, not an automated test: the project never calls a real provider from its tests.
- Speech in will be one clip per answer over HTTP. The streaming relay in `server/tacto/speech.py` stays until then.

## Progress

| Phase | State |
|---|---|
| 0 | Done 22 Nov. Smoke test 3 of 3: speech 0.23 to 0.68 s, transcription 0.58 to 0.70 s, grader 0.14 to 0.53 s. Models in `server/tacto/voice_models.py` |
| 1 | Done 22 Nov. Funnels for steps 4 to 6 are in the lesson file; schema tests in `server/tests/test_funnel_schema.py` |
| 2 | Done 22 Nov. `server/tacto/funnel.py`, 26 tests in `server/tests/test_funnel.py`, including every sequence of six labels |
| 3 | Done 22 Nov. `server/tacto/grader.py`. `scripts/grade_fixtures.py` on `lessons/circuits-101.grading.yaml`: 108 of 111 right (97%), no incorrect answer graded correct, 11 of 11 misconception tags, median 0.34 s an answer |
| 4 | Done 22 Nov. Wired into `lesson.py` and `lab.py` behind `VOICE_ENABLED`; `web/src/ui/Reflection.tsx` has the text box. 37 tests in `server/tests/test_reflection_flow.py` drive every path of all three reflections. With the real grader on a stand-in mat: 0.3 to 0.45 s an answer |
