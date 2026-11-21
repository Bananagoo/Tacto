---
paths:
  - "server/**"
---

# Server rules

- Run things with `uv run` from `server/` (or `make` from the root). Add dependencies with `uv add`, never by editing `pyproject.toml` by hand and never with `pip`.
- `vision/`, `sim/` and `tutor/` do not import each other's internals. They meet in `main.py` through plain data: vision produces parts, wires and a fingertip; sim turns those into a solved `Circuit` and a `Probe`; tutor reads the circuit and the learner's answers.
- Every module must be importable and testable without a camera. Hardware access sits behind a small class with a `replay` implementation that reads `server/fixtures/`.
- `import cv2` only inside `vision/` and `kit/` (and the tooling package `tacto_bench/`).
- Test tooling lives in `server/tacto_bench/`, never in `server/tacto/`. `tacto` must not import `tacto_bench`.
- The solver is DC only: battery, bulbs and resistors as resistances, switch as open or closed. Detect open circuits and shorts in the graph before solving; never hand a singular matrix to NumPy.
- Every solver change needs a test with a hand-worked answer in the docstring.
- LLM, speech and TTS calls live in `tutor/` only, go through one client module, are cached on disk, have a timeout of a few seconds and a non-network fallback. Log model, tokens and milliseconds for each call.
- Never block the event loop: camera reads and model calls run in a thread or task, and the state broadcast keeps its rate.
- Print statements are fine for the hackathon; prefix them with the module name.
