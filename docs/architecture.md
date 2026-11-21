# Architecture

## Data flow

```
                    ┌──────────────────────── server (Python, :8000) ────────────────────────┐
LogiInsight RGB ──> │ vision/camera   frames (camera | replay)                               │
                    │ vision/mat      corner markers → homography → flat mat image           │
                    │ vision/parts    part markers → kind, dots                              │
                    │ vision/wires    ink on each dot-to-dot segment                         │
Hands Tracker ────> │ vision/finger   index_tip → mat coordinates (4-touch calibration)      │
  ws :8765          │ sim/graph       parts + wires → netlist, open/closed/short             │
                    │ sim/solver      DC nodal analysis → current and voltage everywhere     │
                    │ sim/feel        current at the fingertip → pulse_hz                    │
                    │ tutor/          lesson step, prediction check, zone score, learner map │
                    │ main.py         State out at ~15 Hz, events in, over /ws               │
                    └─────────────────────────────────┬──────────────────────────────────────┘
                                                      │ WebSocket /ws (JSON)
                    ┌─────────────────────────────────┴──── web (Chrome, :5173) ─────────────┐
                    │ useTacto        store of the latest State                              │
                    │ bench/          parts, wires, bulb glow, fingertip marker              │
                    │ ui/             tutor prompt, prediction buttons, concept map, zone    │
                    │ haptics/        HapticsDriver: plugin | webhid | console               │
                    │ voice/          mic → utterance → server; plays tutor audio            │
                    └─────────────────────────────────────────────────────────────────────────┘
```

The server holds the truth. The browser renders it and reports what the learner did. There is exactly one WebSocket.

## Contract

`server/tacto/contract.py` defines every message. `web/src/contract.ts` mirrors it by hand.

Server to web:

- `state`, about 15 times a second: `circuit` (status, source voltage, parts, wires with currents), `probe` (fingertip position, what it touches, `pulse_hz`), `tutor` (challenge, phase, prompt, choices, zone), `learner` (concept → unseen | shaky | solid).
- `haptic`, occasional: a one-off pattern the server chose, such as the tutor's `nudge`.

Web to server:

- `wheel` (steps), `answer` (choice, via voice or button), `calibrate_touch` (corner 0–3), `next`.

Who decides what:

- The **server** decides physics and feel: `pulse_hz` is computed from the current at the fingertip, so the mapping lives in one place (`sim/feel`).
- The **web** decides how to render it: which waveform a `tick` is, and the cap on tick rate (`web/src/haptics/`).

HTTP endpoints (add as needed, keep them few): `GET /health`; later `POST /stt` (audio clip → matched choice) and static tutor audio.

## Run modes

| `TACTO_SOURCE` | World comes from | Needs |
|---|---|---|
| (tooling, `make bench`) | `server/tacto_bench/virtual_mat.py`: a mat you change by clicking at `/devtools/#mat`. The real session, solver, lesson engine and database run on top of it. Not a product mode | Nothing |
| `replay` | Frames in `server/fixtures/` plus a recorded fingertip track | Nothing |
| `camera` | LogiInsight RGB stream and the Hands Tracker app | Camera, tracker app running |

Haptics driver is picked in the browser: `console` (flashes a dot, no hardware), `plugin` (Haptic Web plugin), `webhid` (direct, Chrome or Edge).

Record fixtures early: the first time the camera reads the printed mat, save 20 frames of several layouts to `server/fixtures/`. Everyone without the camera develops against those.

## Real-time loop budget

Target: a change on the paper shows on screen in under 250 ms; a fingertip landing on a wire starts the pulse in under 150 ms.

- Mat reading may run slower than the camera (5–10 Hz is fine); the fingertip path runs at tracker rate (~30 Hz).
- When a hand covers part of the mat, keep the last known reading for the hidden segments. Do not let wires flicker while the learner is touching them.
- Smooth every segment's ink decision over a few frames before changing the circuit.
- No network call anywhere in this path.

## Outside the loop

Triggered by lesson events, never per frame, always cached, always with a fallback:

| Call | Trigger | Cache key | Fallback |
|---|---|---|---|
| Speech to text | Learner finished speaking (VAD) | none | Buttons |
| Hint wording | Zone becomes `stuck` | challenge + misconception + step + language | Hint ladder in the lesson YAML |
| Tutor audio | Build time for scripted lines; on demand for hints | hash of text + voice | Browser `speechSynthesis` |

Log every call with model, tokens and milliseconds to `server/logs/calls.jsonl` so we can quote cost per lesson.

## Coordinates

- **Mat grid**: `Dot = (col, row)`, origin top-left. This is what the contract uses.
- **Mat unit square**: `x, y` in 0..1 from the top-left, used for the fingertip.
- **Camera pixels** and **tracker coordinates** never leave `vision/`, with one exception: the live corner preview (`GET /camera/preview`, `vision/preview.py`) streams a small picture of the desk to the page on this machine, so the room can see the learner's hands. It is never stored, shares the camera the vision source already opened, and returns 404 when no camera is open. Nothing else sends pixels. The Hands Tracker's coordinates are mirrored in x, bottom-up in y and relative to a crop; convert them with the calibrated homography, not by hand.

## Configuration

`.env` at the repo root (copy `.env.example`): `TOGETHER_API_KEY`, `OPENROUTER_API_KEY`, `TACTO_SOURCE`, model names. Read with `python-dotenv` in server code only.
