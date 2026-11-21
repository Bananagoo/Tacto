# Tacto

A paper electronics lab. Build a circuit from coloured card pieces on a printed dot-grid mat; a camera reads it; the same circuit runs live on screen. Touch a piece and the MX Master 4 mouse pulses with its current. Turn the scroll wheel to change the battery voltage. On-screen prompts walk through a short lesson.

Built at LauzHack 2026.

## Run it

You need [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) and ngspice (`brew install libngspice`).

```
make setup
make manual      # the lab on a mat you set by hand: http://localhost:8000/manual
```

| Command | What you get |
|---|---|
| `make mock` | A server that replays a recorded 22-second run. No camera, mouse or solver needed |
| `make manual` | The real lab (solver, touch, lesson steps) with the camera replaced by a page you click |
| `make bench` | `make manual` plus the camera bench at `localhost:5173/devtools/` |
| `make kit` | The printable mat, `kit/out/mat.pdf` |
| `make check` | Format, lint, type-check and tests for server and web |

The camera path (reading unmarked card pieces from the mat) is being built; see `docs/roadmap.md`.

## For the lab UI

Everything you need is in [`contract/`](contract/README.md): the JSON schema of the state message, an example, a recorded sample, and how to run the mock and the hand-set mat.

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
