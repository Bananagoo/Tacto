# Roadmap

Where the build stands on 22 Nov 2026. Reset to the core lab on 21 Nov; the state before that reset is the git tag `pre-pivot`.

## Done means

Twenty different layouts read correctly under venue lighting with a hand moving over the mat, and a change on the mat reaches the state message in under half a second. Reported as accuracy and latency numbers.

## Built

| # | Step | State |
|---|---|---|
| 1 | State contract, JSON schema, recorded sample, replay mock | Done. `contract/`, `make mock` |
| 2 | Mat flattening from four corner markers; holding the position through a covered corner | Done. All four markers read at 1080p from the webcam position (22 Nov) |
| 3 | Camera control: manual exposure, brightness calibrated on the paper then held, the autofocus kick | Done (`vision/exposure.py`, `brightness.py`, `focus.py`). Live: settled at gain 6, paper 203, held 12 s |
| 4 | Segment patches and colour reading against the mat's seven colour squares; battery polarity from its red half | Done (`vision/patches.py`, `classify.py`). 20 careless layouts right in each of 9 rendered views; on the printed mat 8 of 8 pieces in 33 of 33 samples, later 15 of 15 and 12 of 12 |
| 5 | Stability and the hand: 3 agreeing frames (8 with a hand about); hand and forearm mask held 0.5 s | Done (`vision/stable.py`, `hands.py`). A still real hand: no change in 12 s. A moving real hand: not yet measured |
| 6 | Graph and solver: open, short, DC current per piece, hand-worked tests | Done (`sim/`) |
| 7 | Fingertip to the nearest piece; current to pulse rate and strength | Done (`lab.py`, `sim/feel.py`). Felt on the mouse by a person |
| 8 | The lab on the camera: `make dev`, 15 state messages a second | Done. `make dev TACTO_SOURCE=replay` runs recorded frames |
| 9 | Lesson: Tinker and Lab modes; the three-step demo lesson (`docs/lab-flow.md`) | Done. Not yet run start to finish on the real mat |
| 10 | Voice reflections (`docs/voice-reflections-plan.md`) | Done, behind `VOICE_ENABLED=1`. Grader 108 of 111; 10 of 10 synthesised spoken answers. Ten answers into a real microphone: not yet done |
| 11 | Setup check: one button that calibrates and checks camera, mat, focus, brightness, colours, speed and voice | Done (`setup_check.py`, `web/devtools/setup/`). 3.4 s on the real camera |

## Still to measure on the hardware

- Twenty layouts on the real mat under venue lighting, with a moving hand.
- The delay from a piece moving to the state changing (estimated 0.2 s).
- Ten spoken answers into a real microphone.
- The demo lesson start to finish on the real mat, at the venue.

## Parked

A free-talking voice tutor, generated tutor speech, an agent loop, LLM-written hints, any LLM call outside the answer grader, learner model, concept map, lab report, freehand sketch reading, 3D parts.
