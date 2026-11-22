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
MatView: placed pieces + fingertip         lab.py (the seam: camera or recorded frames)
  ▼
Lab                                        lab.py
  │  pieces.py   pieces → solver → pieces with current, voltage, resistance, brightness, shorted
  │  sim/        graph analysis (open, short), ngspice, current → pulse rate and strength
  │  lesson.py   which step, whether the circuit completes it
  ▼
State message, 15 a second                 contract.py, app.py (WebSocket /ws)
  ▼
lab UI and mouse haptics                   web/src/ (UI team)
  │
  └── set_voltage ─────────────────────────▶ Lab
```

The fingertip comes from MediaPipe Hand Landmarker on the same frame (`vision/hands.py`) and is mapped onto the mat through the same homography (`flatten.frame_point_to_mat`), then steadied by a One Euro filter (`vision/fingertip.py`). The hand's joints and forearm, padded, are also the mask: segments under a hand keep their reading.

The camera itself is steered from the same thread: manual exposure (`vision/exposure.py`), gain calibrated on the paper and then held (`vision/brightness.py`), and autofocus restarted when the markers go soft (`vision/focus.py`).

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

Tinker is open-ended. Entering Lab starts a fresh lesson at 3 V. Each YAML step has a prompt and circuit/touch goals (counts, arrangement, switch state, minimum voltage and a finger on a live piece). Goals must hold for half a second on a visible mat. Success stays latched; after `linger_seconds` the next step appears. An optional spoken reflection instead waits for an answer or Continue. With `VOICE_ENABLED=1` the answer is transcribed and graded into one of four labels, and code picks the next prewritten line (`funnel.py`, `docs/voice-reflections-plan.md`); only the words and the grade are kept, on the laptop. Restart clears lesson progress and restores 3 V; switching to Tinker preserves the circuit and voltage.

## Product and tooling

| | Product | Tooling |
|---|---|---|
| Server | `server/tacto/` | `server/tacto_mock/` (replay), `server/tacto_bench/` (camera bench) |
| Web | `web/src/` (UI team) | `web/devtools/` |
| Run | `make dev` | `make mock`, `make bench` |

Tooling may import the product; the product never imports tooling (`server/tests/test_boundaries.py`). The fallbacks if the camera misbehaves at the demo are recorded frames (`make dev TACTO_SOURCE=replay`) and the recorded states (`make mock`).

## Measured so far

| What | Number |
|---|---|
| Pieces changing to state message, lab only (solve and send, without the camera) | median 47 ms, worst 86 ms over 30 changes |
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
