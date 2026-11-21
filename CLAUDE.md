# Tacto

Tacto turns a printed paper mat, a pen and a webcam into an electronics lab. A learner places paper components on a dot-grid mat and draws wires; a camera reads the mat; the circuit runs on screen; the MX Master 4 mouse is the bench instrument (scroll wheel sets voltage, vibration is current); a spoken tutor asks for a prediction before every test and keeps the challenge at the learner's level.

This is a LauzHack 2026 project. The only thing that matters is a **3-minute live demo that a judge runs with their own hands**. Prefer the simplest thing that works on stage over the general solution.

## Read before you build

- `docs/tech-stack.md`: every library and model decision, with fallbacks. Check it before adding a dependency.
- `docs/architecture.md`: data flow, the WebSocket contract, run modes.
- `docs/roadmap.md`: phases, gates, who owns what, and the "not now" list.

## Commands

Run from the repo root.

| Command | Does |
|---|---|
| `make setup` | Install server (uv) and web (pnpm) dependencies |
| `make dev` | The product: server on :8000 and web on :5173, both with reload |
| `make bench` | Tooling: the real product on a virtual mat you change by clicking, plus the camera bench. Open `localhost:5173/devtools/` |
| `make server` / `make web` | One side only |
| `make check` | Format check, lint, type-check, tests. Must pass before every commit |
| `make fmt` | Format everything |
| `make kit` | Render the printable mat and parts to `kit/out/` (once `kit/make_kit.py` exists) |

`TACTO_SOURCE=replay|camera` picks where the product's world comes from. Neither is built yet, so until the session loop lands use `make bench`, which needs no hardware.

## Product and tooling

Product code is `server/tacto/` and `web/src/`. Test tooling (the virtual mat, the camera bench, the haptics page) is `server/tacto_bench/` and `web/devtools/`, with its tests in `server/tests/bench/`. Tooling may import the product; the product never imports tooling. `server/tests/test_boundaries.py` enforces this. The design is in `docs/superpowers/specs/2026-11-21-tacto-platform-design.md`.

## Layout and lanes

Four people work in parallel, each with their own Claude Code session. Stay in your lane; if a task needs a file in someone else's lane, say so instead of editing it.

| Lane | Owns |
|---|---|
| Vision | `server/tacto/vision/`, `kit/`, `server/fixtures/` |
| Simulation and haptics | `server/tacto/sim/`, `web/src/haptics/` |
| Front end | `web/src/bench/`, `web/src/ui/`, `web/src/App.tsx` |
| Lesson and pitch | `lessons/`, `server/tacto/tutor/`, `web/src/voice/`, `docs/demo-script.md` |

Shared, change with care and tell the team: `server/tacto/contract.py`, `web/src/contract.ts`, `server/tacto/main.py`, `docs/`, this file.

## Rules

1. **Reuse before build.** Before writing generic functionality or adding a dependency, check `docs/tech-stack.md`, then look for a maintained library (use the `reuse-first` skill). If you add or swap one, update the table in the same commit.
2. **The contract is `server/tacto/contract.py`.** `web/src/contract.ts` mirrors it. Change both in one commit, keep changes additive, and never rename a field someone else reads without telling them.
3. **Nothing in the real-time loop touches the network.** Camera → mat reading → solver → state → screen and haptics must run with Wi-Fi off. LLM, speech-to-text and text-to-speech calls happen outside that loop, are cached, and always have an offline fallback.
4. **Keys stay on the server.** API keys live in `.env` (gitignored) and are read only by server code. Never put a key in `web/`, in a commit, in a log line or in a test. This repository is public.
5. **Every piece runs without hardware.** One camera and one mouse are shared by four people. Vision code must run from recorded frames (`TACTO_SOURCE=replay`), haptics through the `console` driver. Do not write code that only works with the device plugged in.
6. **Do not claim hardware works unless a person confirmed it.** You cannot feel the mouse or see the desk. Say what you ran and what still needs a human check.
7. **No chat window, ever.** The learner never types to or reads a conversation with an AI. The tutor speaks short prompts and listens for a prediction; buttons are the fallback.
8. **Teaching rules are product rules.** Predict before every test. Hints go one step down at a time and never state the answer. The camera does not infer emotion and nothing is recorded.
9. **Stay inside the MVP.** If a request is on the "not now" list in `docs/roadmap.md`, say so and ask before building it.
10. **Physics must be right.** Vibration is current (amps), the wheel is voltage (volts). Never mix the two in code, names, UI text or tutor lines; fixing that confusion is what the lesson teaches.

## Conventions

- Python 3.12, `uv`, `ruff` (line length 100), type hints on public functions, pydantic models at boundaries. Tests in `server/tests/`, named `test_*.py`.
- TypeScript strict, function components, zustand for shared state, Tailwind classes for styling. No enums or parameter properties (`erasableSyntaxOnly` is on).
- Units in names when ambiguous: `pulse_hz`, `source_voltage`, `timeout_ms`.
- Constants that need tuning on real hardware get a `TODO(<lane> owner)` comment and live at the top of the file.
- Comments explain why, not what.

## Git

- Small commits, imperative subject line, one concern each. Run `make check` first.
- Work on `main` in your own lane, or a short branch if the change crosses lanes. `git pull --rebase` before pushing. Use `/sync`.
- Ask before `git push`, before any force operation, and before deleting files you did not create.

## When you finish a task

Say in two or three lines: what changed, what you ran to check it, and what a human still has to verify on the hardware.
