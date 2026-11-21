# Tacto: science within reach

A sheet of paper, a pen and a webcam become an electronics lab. Build a circuit from paper parts on a dot-grid mat, watch it run on screen, and feel the current through the mouse while a spoken tutor keeps the challenge at your level.

Built at LauzHack 2026.

## Quick start

Needs [uv](https://docs.astral.sh/uv/), Node 20+, [pnpm](https://pnpm.io/) and the ngspice library for the circuit solver.

```bash
brew install libngspice   # macOS; the path goes in .env as NGSPICE_LIBRARY_PATH
make setup     # installs server and web dependencies, creates .env
make bench     # the product on a virtual mat, plus dev tools: server on :8000, web on :5173
```

Open http://localhost:5173/devtools/ in Chrome. The Virtual mat tab plays the whole lesson with no hardware: draw the gap, move tiles and rest a fingertip by clicking, with the product running beside it. The camera bench and the haptics page are the other tabs.

`make dev` runs the product itself at http://localhost:5173. It needs a real world source (recorded frames or the camera), which is not built yet.

Put your keys in `.env`. Never commit it; this repository is public.

## Where things are

| Path | What |
|---|---|
| `server/tacto/` | Python: `vision/` reads the mat, `sim/` solves the circuit, `tutor/` runs the lesson, `contract.py` defines every message |
| `web/src/` | React: `bench/` draws the circuit, `ui/` the tutor and concept map, `haptics/` drives the mouse, `voice/` the microphone and audio |
| `server/tacto_bench/`, `web/devtools/` | Test tooling, kept apart from the product: virtual mat, camera bench, haptics page |
| `scripts/` | One-off hardware probes |
| `lessons/` | Lesson content as YAML |
| `kit/` | Printable mat and parts |
| `docs/` | `tech-stack.md` (decisions), `architecture.md`, `roadmap.md` (phases and gates), `hardware-log.md` |

## Working with Claude Code

Start `claude` in the repo root and accept the trust prompt; it lists the allowed commands and the format hook from `.claude/settings.json`.

What is set up:

| Piece | Where | What it does |
|---|---|---|
| Project instructions | `CLAUDE.md` | The product, commands, lanes and ten rules, loaded every session |
| Scoped rules | `.claude/rules/` | Hardware facts, server, web, contract and lesson rules, loaded only when Claude touches matching files |
| `/hardware-check <mouse\|camera\|hands\|kit\|voice>` | skill | Walks you through one device test and logs the result |
| `/gate <phase>` | skill | Checks a roadmap gate; separates what is tested from what needs a person |
| `/sync [message]` | skill | Check, commit, rebase onto main; never pushes on its own |
| `reuse-first` | skill, automatic | Makes Claude look for a library before writing generic code |
| `library-scout` | subagent | Researches candidate libraries in its own context |
| `reviewer` | subagent | Reviews the diff for secrets, contract drift, network in the real-time loop, scope |
| Format hook | `.claude/hooks/format.sh` | Runs ruff or prettier on each file Claude edits |
| Permissions | `.claude/settings.json` | `make`, `uv`, `pnpm` and read-only git run without prompts; `git push` asks; `.env` cannot be read |

Personal overrides go in `.claude/settings.local.json` and `CLAUDE.local.md` (both gitignored).

### First prompt for each lane

Paste one of these to start. Each session should stay in its own lane (table in `CLAUDE.md`).

**Vision**

> I own the vision lane. Read docs/tech-stack.md and docs/roadmap.md phase 1. First write a shared grid-geometry module and kit/make_kit.py so I can print the mat and parts. Then build mat reading in server/tacto/vision/ against saved frames: corner markers, homography, part markers, wire ink per segment. Make it run in replay mode from server/fixtures/. Plan first, then build.

**Simulation and haptics**

> I own the simulation and haptics lane. Read docs/tech-stack.md and docs/architecture.md. Build the DC solver in server/tacto/sim/ (networkx for open and short detection, ngspice through InSpice for the physics) with tests for one bulb, two in series and two in parallel, each with the hand-worked answer in the docstring. Then the function that turns current at the fingertip into pulse_hz. I will run /hardware-check mouse in parallel.

**Front end**

> I own the front end lane. Read docs/architecture.md and web/src/contract.ts. Build the bench view in web/src/bench/ as SVG driven by the State from useTacto: battery, bulb, resistor, switch, wires on the dot grid, bulb glow from brightness, a marker for the fingertip. Develop against mock mode. Move the current App.tsx harness behind ?dev. Show me a plan and a sketch of the layout first.

**Lesson and pitch**

> I own the lesson lane. Read .claude/rules/lessons.md and lessons/circuits-101.yaml. Write the three MVP challenges (light the bulb, series, parallel) with prediction choices, answers and hint ladders, then the pydantic lesson model and the tutor state machine in server/tacto/tutor/ (zone score rule and concept mastery) with tests. No model calls yet; hints come from the YAML ladder.
