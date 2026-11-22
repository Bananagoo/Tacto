# Tacto

A paper electronics lab. Build a circuit from coloured card pieces on a printed dot-grid mat; a camera reads it; the same circuit runs live on screen. Touch a piece and the MX Master 4 mouse pulses with its current. Turn the scroll wheel to change the battery voltage. Tinker freely, or choose Lab for six guided steps and spoken reflection questions.

Built at LauzHack 2026.

## Run it

You need [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) and ngspice (`brew install libngspice`).

```
make setup
make dev         # the lab on the camera; or `make mock` for recorded states, no hardware
```

| Command | What you get |
|---|---|
| `make mock` | A server that replays a recorded 90-second run (Continue advances reflections). No camera, mouse or solver needed |
| `make dev` | The lab on the camera looking at the printed mat. The setup check is at `localhost:5173/devtools/#setup` (or **Dev tools** on the home page) |
| Setup check | Before a demo: with `make dev` running, open `localhost:5173/devtools/#setup` and press **Run the check** |
| `VOICE_ENABLED=1 make dev` | The same, with spoken reflections: the lab asks its questions aloud, hears the answer and narrows the question if it misses. Needs `TOGETHER_API_KEY` in `.env` and the network; see `docs/voice-reflections-plan.md` |
| `make bench` | The camera bench at `localhost:5173/devtools/`: the camera's picture, the flattened mat, each segment's reading |
| `make kit` | The printable mat, `kit/out/mat.pdf` |
| `make check` | Format, lint, type-check and tests for server and web |

The camera path reads the printed pieces from the mat; see `docs/roadmap.md` for what has been checked on the real desk.

## For the lab UI

Everything you need is in [`contract/`](contract/README.md): the JSON schema of the state message, an example, a recorded sample, and how to run the mock.

## How it works

```
camera frame → flatten the mat (4 corner markers) → one patch per dot-to-dot segment
  → classify each patch (empty, wire, battery, bulb, resistor, switch)
  → circuit graph → solver → one state message, 15 times a second → lab UI and mouse
```

See `docs/architecture.md`.

## Layout

| Path | What it is |
|---|---|
| `server/` | Python: camera, mat reading, circuit solver, lesson steps, the WebSocket |
| `web/` | The lab UI (React) and the dev tools |
| `contract/` | The state contract, generated from `server/tacto/contract.py` |
| `lessons/` | Lesson steps as YAML |
| `kit/` | The printable mat |
| `docs/` | Architecture, roadmap, tech stack, hardware log |
