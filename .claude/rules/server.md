---
paths:
  - "server/**"
---

# Server rules

- Run things with `uv run` from `server/` (or `make` from the root). Add dependencies with `uv add`, never by editing `pyproject.toml` by hand and never with `pip`. Ask before adding one.
- The flow is one direction: `vision/` → `MatView` → `lab.py` → `State`. `vision/` and `sim/` do not import each other. `sim/` keeps its own types (`sim/types.py`); `pieces.py` translates.
- Every module must be importable and testable without a camera. The camera and the hand tracker sit behind the small protocols in `vision/frames.py`, with a folder-of-frames implementation for replay.
- `import cv2` only inside `tacto/vision/`, `tacto_bench/`, `kit/` and `scripts/`.
- Tooling lives in `tacto_bench/` and `tacto_mock/`, never in `tacto/`. `tacto` must not import either.
- The solver is DC only: battery, bulbs and resistors as resistances, switch as open or closed. Detect open circuits and shorts in the graph before solving.
- Every solver change needs a test with a hand-worked answer in the docstring.
- Never block the event loop: camera reads, hand tracking and solves run in a thread, and the state broadcast keeps its rate.
- No network calls anywhere in `tacto/`. The live loop runs with Wi-Fi off.
- Vision results are reported as numbers: per-class accuracy on held-out layouts, latency in milliseconds.
- Print statements are fine for the hackathon; prefix them with the module name.
