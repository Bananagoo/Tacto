# Lessons

One YAML file per lesson. The server loads and validates them at startup (pydantic model in `server/tacto/tutor/`, to be written by the lesson lane). Changing wording must never need a code change.

Rules for writing them are in `.claude/rules/lessons.md`. In short: build → predict → test → explain; spoken lines of one sentence; hints step down and never give the answer; vibration is current, the wheel is voltage.

`circuits-101.yaml` is a draft showing the shape. The wording is a placeholder for the lesson lane to replace.
