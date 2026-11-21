# Wave plans

Agreed on 21 Nov 2026: the build runs as parallel waves. One implementer subagent per lane, each in its own git worktree. The orchestrating session reviews each result, merges it, runs `make check`, pushes, then stops for the user's review before the next wave.

## Rules for every lane

1. **Reuse first.** Run the `reuse-first` skill before writing generic code. Do not add a dependency yourself: report the candidate (name, licence, install command, why) and the orchestrator takes it to the user.
2. **Stay in your lane's files** (table in `CLAUDE.md`). Only the orchestrator edits `server/tacto/contract.py`, `web/src/contract.ts`, `server/tacto/main.py`, `docs/` and `CLAUDE.md`. If the contract is missing something, say what and stop.
3. **Tests first** on the server side, and no network in any test.
4. **No hardware.** Everything in Wave 1 must run on a laptop with nothing plugged in.
5. **Finish with** `make check` output, the files touched, and what a person still has to verify.

## Wave 1: prove each piece without hardware

| Plan | Lane |
|---|---|
| [wave1-sim.md](wave1-sim.md) | Simulation and haptics |
| [wave1-vision.md](wave1-vision.md) | Vision and paper kit |
| [wave1-frontend.md](wave1-frontend.md) | Front end |
| [wave1-lesson.md](wave1-lesson.md) | Lesson and tutor |

## Later waves (not planned in detail yet)

- **Wave 2, core loop:** a real world object in `main.py` that replaces the mock: mat reading → `sim` → `State`, the tutor driving `State.tutor`, wheel setting the voltage. Wire reading from flattened frames. Replay mode from fixtures.
- **Wave 3, hardware and voice:** camera capture, Hands Tracker client and 4-touch calibration, speech in, tutor audio, hint wording from the model.
