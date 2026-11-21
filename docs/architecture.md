# Architecture

One server process on one laptop turns camera frames into state messages. The lab UI in the browser draws them and drives the mouse. Nothing in this loop touches the network.

## The loop

```
camera frame (colour, 1080p, ~30 fps)
  │  vision/camera.py                      one worker thread per camera
  ▼
flatten                                    vision/flatten.py, vision/tracker.py
  │  find the four ArUco corner markers, fit a homography, warp to a square-on page;
  │  with a corner covered, keep the last position while the visible corners still agree
  ▼
segment patches                            vision/patches.py
  │  one fixed-size crop for every gap between neighbouring dots
  ▼
classify each patch                        vision/classify.py, kit/pieces.yaml
  │  empty | wire | bulb | resistor | switch closed | switch open | battery (+ end) | unsure
  │  every pixel goes to the nearest of the mat's seven colour squares, read each frame;
  │  red beside black is a battery and the red end is positive
  ▼
stability                                  vision/stable.py
  │  a segment changes only after 3 frames agree; unsure segments and segments under a
  │  hand hold; nothing is read off a frame no corner marker backs (it may be soft)
  ▼
                                           vision/source.py runs all of the above on one
                                           thread, with vision/focus.py keeping the focus
  ▼
MatView: placed pieces + fingertip         lab.py (the seam: camera or hand-set mat)
  ▼
Lab                                        lab.py
  │  taps.py     hand-set mat only: a pointer dwelling on a switch for 0.5 s toggles it
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

- **Touch.** MediaPipe gives a fingertip position, not contact. A fingertip over a segment counts as touching it.

A switch's state and a battery's polarity it can see: open and closed switches are different pieces (cyan and green), and a battery is red at its positive end and black at the other.

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

| Flatten one 1080p frame | median 3.7 ms |
| Cut and classify all 93 segments | median 7.2 ms |
| Colour baseline on rendered images | 20 of 20 random layouts right in each of 10 views (blur, dim, noise, tilt, half turn) |

On the printed mat, 22 Nov 2026 (one layout, one desk, nobody's hands in view; `docs/hardware-log.md`):

| What | Number |
|---|---|
| Pieces read right | 8 of 8, the same in 33 of 33 samples over 8 seconds |
| State messages from the camera | 15 a second |
| Time per frame | flatten 6 ms, hand 27 ms, read 10 ms (26 ms before it was sped up; 10 ms is from a rendered frame) |

Not measured yet: more layouts, hands over the mat, and the delay from a piece moving to the state changing. Three agreeing frames at about 20 frames a second is roughly 0.15 s, plus up to 0.07 s for the next message.
