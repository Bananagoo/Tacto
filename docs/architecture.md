# Architecture

One server process on one laptop turns camera frames into state messages. The lab UI in the browser draws them and drives the mouse. Nothing in this loop touches the network.

## The loop

```
camera frame (colour, 1080p, ~30 fps)
  │  vision/camera.py                      one worker thread per camera
  ▼
flatten                                    vision/flatten.py
  │  find the four ArUco corner markers, fit a homography, warp to a square-on page
  ▼
segment patches                            NOT BUILT
  │  one fixed-size crop for every gap between neighbouring dots
  ▼
classify each patch                        NOT BUILT
  │  empty | wire | battery | bulb | resistor | switch
  │  baseline: HSV colour per piece type; then a small classifier on our own patches
  ▼
stability                                  NOT BUILT
  │  a segment changes only after N frames agree; segments under a hand hold
  ▼
MatView: placed pieces + fingertip         lab.py (the seam: camera or hand-set mat)
  ▼
Lab                                        lab.py
  │  taps.py     fingertip dwelling on a switch for 0.5 s toggles it
  │  pieces.py   pieces → solver → pieces with current, brightness, shorted
  │  sim/        graph analysis (open, short), ngspice, current → pulse rate
  │  lesson.py   which step, whether the circuit completes it
  ▼
State message, 15 a second                 contract.py, app.py (WebSocket /ws)
  ▼
lab UI and mouse haptics                   web/src/ (UI team)
  │
  └── set_voltage ─────────────────────────▶ Lab
```

The fingertip comes from MediaPipe Hand Landmarker on the same frame (`vision/hands.py`, `vision/live.py`) and is mapped onto the mat through the same homography (`flatten.frame_point_to_mat`). The hand's landmarks, padded, will also be the mask for "segments under a hand keep their value".

## The mat model

The mat is a grid of dots (`kit/mats/<id>.yaml`: columns, rows, dot spacing). A dot is `[col, row]`, origin top-left. Every piece lies on one **segment**: the gap between two dots that are neighbours in a row or a column. A piece's id is its segment, `"c,r-c,r"` with the top-left dot first.

Dots are nodes and pieces are edges. Wires and closed switches conduct freely; bulbs and resistors resist; an open switch is a gap; a battery is the source, with `a` its positive end.

## Circuit status

| Status | Meaning |
|---|---|
| `open` | No complete loop through a battery. An empty mat is open |
| `working` | Current flows through at least one piece |
| `shorted` | A loop through the battery with nothing in it to resist. `shorted_path` lists the pieces round it |

Open circuits and shorts are found in the graph (`sim/graph.py`) before the solver is called, so ngspice only ever sees a circuit with a unique answer. A wire across one of two series bulbs is not a short: the circuit works and that bulb is dark.

## What the camera cannot see

- **Switch open or closed.** The learner taps the paper switch. The lab remembers which switches have been tapped; a switch lifted off the mat is forgotten and a new one starts open.
- **Touch.** MediaPipe gives a fingertip position, not contact. A fingertip over a segment counts as touching it.
- **Battery polarity.** A plain coloured card has no marked end. Until the kit marks one, the reader will pick by rule.

## Lesson steps

A lesson (`lessons/<id>.yaml`) is a fixed list of steps. Each has a prompt and a `done_when` (status, number of batteries, bulbs, lit bulbs, series or parallel). A step is done once its goal has held for half a second; it stays done; after `linger_seconds` the next prompt appears. There are no predictions to score, no hints and no timers on the learner.

## Product and tooling

| | Product | Tooling |
|---|---|---|
| Server | `server/tacto/` | `server/tacto_mock/` (replay), `server/tacto_bench/` (hand-set mat, camera bench) |
| Web | `web/src/` (UI team) | `web/devtools/` |
| Run | `make dev` | `make mock`, `make manual`, `make bench` |

Tooling may import the product; the product never imports tooling (`server/tests/test_boundaries.py`). The hand-set mat is the fallback if the camera misbehaves at the demo: it feeds the same `Lab` through the same seam.

## Measured so far

| What | Number |
|---|---|
| Hand-set mat change to state message | median 47 ms, worst 86 ms over 30 changes |
| `set_voltage` to state message | 69 ms |
| First solve after startup | 365 ms (done at startup) |
| Later solves | about 1 ms |
| MediaPipe hand tracking | about 26 ms a frame at 1080p |

Camera-path latency and accuracy are not measured yet.
