# Tacto

Tacto is a paper electronics lab. A student builds a circuit from coloured card pieces on a printed dot-grid mat. A camera above the desk reads it. The same circuit appears live in an on-screen lab. The student interacts by touch and through the MX Master 4 mouse: a haptic pulse is current, the scroll wheel is voltage. On-screen prompts walk them through a fixed set of lesson steps.

That is the whole product for now. This is a LauzHack 2026 project and the only thing that matters is a **3-minute live demo that a judge runs with their own hands**, on one macOS laptop, with Wi-Fi off. Prefer the simplest thing that works on stage.

## Parked: do not build, extend or wire in

Voice tutor, speech-to-text, text-to-speech, voice detection, an agent loop, LLM hints and any Together or OpenRouter calls, zone score, learner model, concept map, lab report, freehand sketch reading, 3D parts. If a request touches one of these, say so and ask first. The code that existed for them is at the git tag `pre-pivot`.

## Read before you build

- `docs/architecture.md`: the data flow from camera frame to state message, and where each step lives.
- `contract/README.md`: the state contract, the recorded sample and the mock, as the UI team sees them.
- `docs/roadmap.md`: the build order, what is done, and what "done" means.
- `docs/tech-stack.md`: every library decision and the hardware facts. Check it before adding a dependency.

## Who owns what

| Lane | Owner | Owns |
|---|---|---|
| Vision and circuit state | Katie | `server/` (camera frame to state message), `contract/`, `scripts/`, `web/devtools/` |
| Lab UI | Two teammates | `web/src/`: visuals, WebSocket client, haptics, scroll wheel, prompt panel |
| Kit and lesson | One teammate | The physical mat and card pieces, the camera mount, lesson wording in `lessons/` |

Stay in your lane. **Do not edit `web/src/`** from the vision lane: what the UI team gets from us is the contract, the recorded sample and the mock. If a task needs a file in another lane, say so instead of editing it.

## Commands

Run from the repo root.

| Command | Does |
|---|---|
| `make setup` | Install server (uv) and web (pnpm) dependencies |
| `make camera-tool` | Build `uvc-util` into `server/vendor/` (macOS, needs the network once). `make setup` runs it. Without it the camera stays on auto-exposure |
| `make mock` | Replay the recorded sample on `ws://localhost:8000/ws`. No camera, mouse or solver needed |
| `make manual` | The real lab on a mat you set by hand. Open `localhost:8000/manual` |
| `make bench` | `make manual` plus the web dev tools (camera bench at `localhost:5173/devtools/`) |
| `make dev` | The lab on the camera, with the web UI. Not usable until the camera reader is built |
| `make check` | `make check-server` and `make check-web`: format, lint, type-check, tests. Must pass before every commit |
| `make contract` / `make sample` | Regenerate `contract/` after a contract change |
| `make kit` | Write the printable mat to `kit/out/mat.pdf` from `kit/mats/circuits-101.yaml` |
| `make fmt` | Format everything |

## Layout

| Path | What it is |
|---|---|
| `server/tacto/contract.py` | The one state message and the one browser message. Source of `contract/` |
| `server/tacto/lab.py` | Mat source in, `State` out: solves, finds the touched piece, taps switches, runs the lesson |
| `server/tacto/pieces.py` | Pieces on segments to the solver and back |
| `server/tacto/sim/` | Graph analysis (open, short), the ngspice solver, current to pulse rate |
| `server/tacto/lesson.py`, `lessons/` | Lesson steps as data; each completes from the circuit |
| `server/tacto/taps.py` | A switch tap is a half-second fingertip dwell |
| `server/tacto/mat.py`, `kit/mats/` | The mat: grid size and dot spacing as data |
| `server/tacto/vision/` | Camera, manual exposure, hand tracking, corner markers, flattening, holding the mat's position (`tracker.py`), the printable mat |
| `server/tacto_mock/`, `server/tacto_bench/` | Tooling: the replay mock, the hand-set mat, the camera bench |
| `web/devtools/` | Tooling pages for the vision lane (camera bench, haptics test page) |

Tooling may import the product (`server/tacto/`); the product never imports tooling. `server/tests/test_boundaries.py` enforces this.

## Decided: do not revisit

- Wires are card strips, classified like any other piece. There are no pen lines.
- The mat has four ArUco corner markers. The pieces have none.
- The circuit solver runs on the server.
- A switch is two printed pieces, open (cyan) and closed (green). The learner swaps the piece and the camera reads which one is down. Decided 21 Nov; it replaces the finger tap. `taps.py` and the tap wording in `contract/README.md` are still there until the camera reader lands.
- Fingertip tracking is MediaPipe on our own colour frames.

## Still open: ask, do not assume

- Grid size and dot spacing (config in `kit/mats/circuits-101.yaml`; the current values are placeholders).
- Nothing on colours: the printed pieces are in `kit/printed/` and their colours are listed in `kit/printed/README.md`. `kit/pieces.yaml` still holds the old proposal and does not match them yet.

## Rules

1. **Reuse before build.** Before writing generic functionality or adding a dependency, check `docs/tech-stack.md`, then use the `reuse-first` skill and verify the package before relying on it.
2. **The contract is `server/tacto/contract.py`.** Changes need Katie's sign-off. After a change run `make contract` and `make sample`, and tell the UI team.
3. **The live loop runs with Wi-Fi off.** Camera → flatten → classify → solver → state → screen and haptics never touches the network.
4. **Every piece runs without hardware.** One camera and one mouse are shared. Vision code must run from recorded frames; the lab must run from the hand-set mat.
5. **Do not claim hardware works unless a person confirmed it.** You cannot feel the mouse or see the desk. Say what you ran and what still needs a human check.
6. **Small steps, tests with each one, results before moving on.** Report accuracy and latency as numbers, not impressions.
7. **Physics must be right.** Vibration is current (amps), the wheel is voltage (volts). Never mix the two in code, names or prompts.
8. **Secrets stay out of the repo.** It is public. `.env` is gitignored.
9. **Nothing from the camera is stored** except frames a person records on purpose into `server/fixtures/`, and those must not show faces.

## Conventions

- Python 3.12, `uv`, `ruff` (line length 100), type hints on public functions, pydantic models at boundaries. Tests in `server/tests/`, named `test_*.py`. Every solver change needs a test with a hand-worked answer.
- Units in names when ambiguous: `pulse_hz`, `dot_pitch_mm`, `x_px`.
- Constants that need tuning on real hardware get a `TODO(<owner>)` comment and live at the top of the file.
- Comments explain why, not what.
- `import cv2` only inside `server/tacto/vision/`, `server/tacto_bench/`, `kit/` and `scripts/`.

## Git

- The reset lives on the branch `core-lab` until the UI team is ready for the new contract; then it merges to `main`.
- Small commits, imperative subject line, one concern each. Run `make check` first.
- Never force-push. Ask before deleting files you did not create.

## When you finish a task

Say in two or three lines: what changed, what you ran to check it (with the numbers), and what a person still has to verify on the hardware.
