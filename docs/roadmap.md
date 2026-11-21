# Roadmap

Reset on 21 Nov 2026 to the core lab. The state before the reset is the git tag `pre-pivot`. Work is on the branch `core-lab`, merged to `main` when the UI team is ready for the new contract.

## Done means

Twenty different layouts read correctly under venue lighting with a hand moving over the mat, and a change on the mat reaches the state message in under half a second. Reported as accuracy and latency numbers.

## Build order (vision and circuit state lane)

| # | Step | State |
|---|---|---|
| 1 | State contract, JSON schema, recorded sample, replay mock | Done. `contract/`, `make mock` |
| 2 | Mat flattening: four corner markers to a homography | Done on rendered images (30 tests, incl. blur, dim, tilt, upside down). Not yet on real paper |
| 3 | Segment patches: one fixed-size crop per dot-to-dot segment | Done on rendered images. `vision/patches.py` |
| 4 | Classification per segment: HSV colour baseline, then a small classifier | Colour baseline done on rendered images with the proposed colours (`vision/classify.py`, `kit/pieces.yaml`): 20 of 20 layouts in each of 10 views. The trained classifier waits for real patches (step 5) |
| 5 | Capture tool: labelled patches from the real camera given a known layout; held-out layouts; per-class accuracy | Not started |
| 6 | Stability: N consecutive frames; segments under a hand hold (MediaPipe landmarks as the mask) | Not started |
| 7 | Graph and solver: open, short, DC current per piece, hand-worked tests | Done. One bulb, series, parallel, short across a bulb, bypassed bulb |
| 8 | Finger: fingertip to mat to nearest segment; switch tap with debounce | Logic done and tested on the hand-set mat. Not yet on the camera |
| 9 | Lesson steps: fixed sequence, each completes from the circuit | Done. Wording is placeholder |

Also built: the hand-set mat (`make manual`), for the UI team to trigger any state and as the demo fallback.

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
