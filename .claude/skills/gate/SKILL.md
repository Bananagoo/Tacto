---
name: gate
description: Check whether a roadmap step is really done. Use when the user runs /gate or asks "are we done with step N" or "can we move on".
argument-hint: "[step number 1-9]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(make *) Bash(git log *) Bash(git status *) Bash(uv run *) Bash(pnpm *)
---

Check step $ARGUMENTS of the build order in `docs/roadmap.md`. If no step was given, check the earliest one that is not done, and the overall "Done means" line.

## Steps

1. Read the step and the "Done means" line in `docs/roadmap.md`.
2. Run `make check`. If it fails, the gate fails; report the failure and stop.
3. For each thing the step must do, find the evidence:
   - **Automated**: a test, a fixture, or a command you can run now with the mock, the hand-set mat or recorded frames. Run it.
   - **Human**: anything about the real camera, the real mouse, lighting, sound or how something feels. You cannot verify these. Look for a dated entry in `docs/hardware-log.md`; if there is none, mark it "needs a person".
4. Check that nothing from the "Parked" list has been built.

## Report

A table with one row per condition: condition, evidence, status (pass, fail, needs a person). Then one line: **gate passes**, **gate fails**, or **gate waits on N human checks**, followed by the shortest list of what to do next and which lane does it.

Do not mark a hardware condition as passed on the strength of code existing. Do not fix anything as part of this check; report only.
