---
name: reuse-first
description: Check for an existing library, model or tool before building. Use before adding a dependency, vendoring code, or writing more than about 40 lines of generic functionality (geometry, image processing, audio, parsing, UI widgets, API clients), and whenever the user says "is there a library for".
argument-hint: "[what you need]"
---

Our rule is reuse before build. Find out whether $ARGUMENTS already exists before writing it.

## 1. Check what is already decided

Read `docs/tech-stack.md`. If the job has a row, use that decision. If the row's status is "test" and the test has failed, use its fallback and update the row. Do not reopen a decision that is working.

## 2. Look in what is already installed

`server/pyproject.toml` and `web/package.json`. OpenCV, NumPy, networkx, pydantic, the browser platform and React cover more than you expect. Prefer a function in a library we already have over a new dependency.

## 3. Search, with a ten-minute limit

For anything bigger, delegate to the `library-scout` subagent so the search does not fill this conversation. Ask it for at most three candidates.

A candidate qualifies only if all of these hold:

- Installs with one `uv add` or `pnpm add` on macOS arm64, with no system packages and no compile step.
- Released or committed to within the last 18 months, or small and stable enough that this does not matter.
- Does the job with less glue code than writing it would take.
- For the real-time loop: runs locally, no network.

## 4. Decide and record

- **Reuse**: add it with `uv add` or `pnpm add`, write the thinnest wrapper that fits our interfaces, and add or update the row in `docs/tech-stack.md` (decision, source, fallback, check).
- **Build**: if nothing qualifies, write it, and add one line under "Built ourselves, and why" in `docs/tech-stack.md`.

Either way, tell the user in two lines what you chose and why. If the choice replaces something another lane depends on, stop and ask first.

## Already ruled out

CircuitJS1 as the main simulator (GPL-2.0, iframe), PySpice (unmaintained; we use its fork InSpice) and lcapy for the solver, LangChain or any agent framework, a database, the camera's face AI, Logi Gaze Tracker. Reasons are in `docs/tech-stack.md`.
