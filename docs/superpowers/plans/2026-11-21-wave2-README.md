# Wave 2: build the platform without hardware

**Spec:** `docs/superpowers/specs/2026-11-21-tacto-platform-design.md`

Four lanes run in parallel, one implementer per lane, each in its own git worktree. The orchestrator reviews and merges each lane, then runs `make check`.

| Plan | Lane | Owns |
|---|---|---|
| `2026-11-21-wave2-sim.md` | Simulation | `server/tacto/sim/`, `server/tests/sim/` |
| `2026-11-21-wave2-store.md` | Store and lesson content | `server/tacto/store/` (except `repositories.py`), `server/tacto/lessons/loader.py`, `lessons/`, `server/tests/store/` |
| `2026-11-21-wave2-engine.md` | Lesson engine and learner model | `server/tacto/lessons/` (except `models.py`, `loader.py`), `server/tacto/learner/` (except `models.py`), `server/tests/lessons/`, `server/tests/learner/` |
| `2026-11-21-wave2-web.md` | Product web app | `web/src/` (except `contract.ts`, `haptics/driver.ts`) |

## Frozen for this wave

These were written by the orchestrator before the wave. Do not edit them. If one is wrong or missing something, stop and say so in your report.

- `server/tacto/contract.py` and `web/src/contract.ts`
- `server/tacto/lessons/models.py`, `server/tacto/learner/models.py`, `server/tacto/store/repositories.py`
- `server/tacto/app.py`, `server/tacto/world.py`, `server/tacto/main.py`
- `server/pyproject.toml`, `server/uv.lock`, `web/package.json`, `web/pnpm-lock.yaml` (no new dependencies; report any you want)
- Everything under `docs/`, `.claude/`, `CLAUDE.md`, `Makefile`, `server/tacto_bench/`, `web/devtools/`

## Global constraints

- Read `CLAUDE.md` and the rules file for your area in `.claude/rules/` first.
- Product code must be clean, readable and modular: small files with one job, type hints on public functions, names with units (`pulse_hz`, `source_voltage`), comments that explain why. No dead code, no speculative options.
- Product code never imports `tacto_bench` or `web/devtools`.
- Tests first. No test may touch the network, the camera or the mouse.
- Physics words are exact: vibration is current (amps), the wheel is voltage (volts).
- Tunable constants sit at the top of their file with a `TODO(<lane> owner)` note.
- Set up your worktree with `make setup` (it has no `.venv` or `node_modules` yet).
- Finish with `make check` passing. Commit on your worktree's branch with small, imperative commits. Do not push, and do not merge.

## Report back

What you built, the files, the exact `make check` result with test counts, anything you could not do, and anything a person must verify on hardware.
