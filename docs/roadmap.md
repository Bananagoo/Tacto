# Roadmap

Reset on 21 Nov 2026 to the core lab. The state before the reset is the git tag `pre-pivot`. Work is on the branch `core-lab`, merged to `main` when the UI team is ready for the new contract.

## Done means

Twenty different layouts read correctly under venue lighting with a hand moving over the mat, and a change on the mat reaches the state message in under half a second. Reported as accuracy and latency numbers.

## Build order (vision and circuit state lane)

| # | Step | State |
|---|---|---|
| 1 | State contract, JSON schema, recorded sample, replay mock | Done. `contract/`, `make mock` |
| 2 | Mat flattening: four corner markers to a homography | Done. Works on the printed mat (22 Nov): all four markers read at 1080p from the webcam position |
| 2b | Hold the mat's position while a hand covers a corner marker (`vision/tracker.py`); manual exposure (`vision/exposure.py`) | Built, 21 Nov. Tracker tested on rendered images. On the real desk manual exposure fixed the burnt-out paper. Focus cannot be locked on this camera (see `docs/hardware-log.md`) |
| 3 | Segment patches: one fixed-size crop per dot-to-dot segment | Done on rendered images. `vision/patches.py` |
| 4 | Classification per segment | Done (`vision/classify.py`): each patch matched to the mat's seven colour squares; battery polarity from its red half; open and closed switches as different pieces. 20 careless layouts right in each of 9 rendered views; 8 of 8 pieces right on the printed mat (one layout) |
| 5 | Capture tool: labelled patches from the real camera; held-out layouts; per-class accuracy | Not built. No trained classifier is needed so far; what is missing is the 20-layout accuracy number on the real mat |
| 6 | Stability: 3 agreeing frames; unsure segments and segments under a hand hold | Done on rendered frames (`vision/stable.py`, `vision/source.py`). Not tried with real hands |
| 7 | Graph and solver: open, short, DC current per piece, hand-worked tests | Done. One bulb, series, parallel, short across a bulb, bypassed bulb |
| 8 | Finger: fingertip to mat to nearest segment | Wired to the camera (`vision/source.py`); tested with a fake hand on rendered frames. Not tried with a real hand. Switches no longer toggle by tap on the camera: the learner swaps the piece |
| 9 | Lesson steps: fixed sequence, each completes from the circuit | Done. Wording is placeholder |

| 10 | The lab on the camera: `make dev` | Runs (`tacto/main.py`): 15 state messages a second from the real camera, 22 Nov. `GET /debug/reader` shows what the reader sees and the milliseconds per step. `make dev TACTO_SOURCE=replay` runs recorded frames |

Removed on 22 Nov: the hand-set mat (`make manual`). The UI team builds against `make mock`; the demo fallbacks are recorded frames and the recorded states.

## Waiting on other lanes

| What | Who | Blocks |
|---|---|---|
| Grid size and dot spacing | Kit owner | Printing the final mat; patch size (step 3) |
| Colour of each piece type, and the card itself | Kit owner | Steps 4 and 5 |
| A mark for the battery's positive end | Kit owner | Current direction on screen |
| Camera mounted straight above the mat, paper filling the frame | Kit owner | Any real-camera number |
| Lesson wording | Kit owner | Nothing; edit `lessons/circuits-101.yaml` |
| Adopting the new contract in `web/src/` | UI team | Merging `core-lab` to `main` |

## Needs a person on the hardware

- Print `kit/out/mat.pdf` at 100% and check the 50 mm bar.
- Check the corner markers are found under hall lighting (`make bench`, camera tab, Markers).
- Feel the pulse rates (1.5, 3 and 6 Hz) and the short-circuit buzz on the real mouse.
- Try the half-second switch tap with a real hand.

## Parked

Voice tutor, speech-to-text, text-to-speech, voice detection, the agent loop, LLM hints and any Together or OpenRouter calls, zone score, learner model, concept map, lab report, freehand sketch reading, 3D parts.
