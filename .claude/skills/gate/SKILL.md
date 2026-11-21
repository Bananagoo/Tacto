---
name: gate
description: Check whether a roadmap phase gate passes. Use when the user runs /gate or asks "are we done with phase N" or "can we move on".
argument-hint: "[phase number 1-5]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(make *) Bash(git log *) Bash(git status *) Bash(uv run *) Bash(pnpm *)
---

Check gate $ARGUMENTS from `docs/roadmap.md`. If no phase was given, work out the earliest phase whose gate has not passed and check that one.

## Steps

1. Read the phase and its gate in `docs/roadmap.md`.
2. Run `make check`. If it fails, the gate fails; report the failure and stop.
3. For each "done when" condition of the phase, find the evidence:
   - **Automated**: a test, a fixture, or a command you can run now in `mock` or `replay` mode. Run it.
   - **Human**: anything about the real camera, the real mouse, lighting, sound or how something feels. You cannot verify these. Look for a dated entry in `docs/hardware-log.md`; if there is none, mark it "needs a person".
4. Check that nothing from the "not now" list has been built.

## Report

A table with one row per condition: condition, evidence, status (pass, fail, needs a person). Then one line: **gate passes**, **gate fails**, or **gate waits on N human checks**, followed by the shortest list of what to do next and which lane does it.

Do not mark a hardware condition as passed on the strength of code existing. Do not fix anything as part of this check; report only.
