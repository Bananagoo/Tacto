# The state contract

What the server and the lab UI say to each other. The Python models in
`server/tacto/contract.py` are the source; everything here is generated from
them. Changes need the vision owner's sign-off.

| File | What it is |
|---|---|
| `state.schema.json` | JSON schema of the one message the server sends, about 15 times a second |
| `set_voltage.schema.json` | Set battery voltage (0–9 V) |
| `set_mode.schema.json` | Choose `tinker` or `lab` |
| `restart_lesson.schema.json` | Restart Lab at step one and 3 V |
| `continue_lesson.schema.json` | Acknowledge a reflection with its `step_id` |
| `example-state.json` | One state: a bulb on a closed loop at 6 V, a finger on the bulb |
| `example-set-voltage.json` | One browser message |
| `sample-states.jsonl` | About 90 seconds: switches, touch, voltage 3 → 6 V, series, parallel and spoken reflections; no short |

## Run the mock

    make mock

It replays `sample-states.jsonl` on `ws://localhost:8000/ws`, looping, with `seq`
and `t` counting up. It needs no camera, mouse or solver. The replay starts in Lab
and waits at reflections until `continue_lesson`. Restart rewinds the recording;
mode changes work, and entering Lab rewinds. It accepts `set_voltage` and logs it,
but recorded circuit numbers do not react to the wheel.

## Reading a state

- Dots are `[col, row]`, origin top-left. `grid` gives the number of dots.
- Every piece lies between two neighbouring dots, `a` and `b`. Its `id` is that
  segment, `"c,r-c,r"` with the top-left dot first.
- `voltage` is the volts across the piece: what a multimeter would read on it. A wire
  and a closed switch read 0.
- `current` is in amps, positive from `a` to `b`. A battery's `a` is its positive
  end, so its own current reads negative; use `circuit.total_current` for the size.
- `brightness` (bulbs only) runs 0 to 1. `closed` is set on switches only.
- `circuit.status` is `working`, `open` or `shorted`. When shorted,
  `circuit.shorted_path` lists the piece ids round the loop, and each has `shorted: true`.
- `touch` is the fingertip. `x`, `y` run 0 to 1 from the first dot column/row to the
  last. Play `pulse_hz` ticks a second on the mouse, at `strength` (0 to 1) of the
  mouse's vibration range; if `buzz` is true play one hard continuous buzz. Both follow
  the current through the touched piece, so more bulbs in series feel slower and
  fainter and the battery wire of a parallel circuit feels faster and stronger.
  Vibration is current, never voltage.
- `mat_visible: false` means the camera has lost the mat; pieces hold their last values.
- `mode` is `tinker` or `lab`. The live app starts in Tinker, with empty lesson fields
  and no progression. Entering Lab starts a fresh run at 3 V. Returning to Tinker
  preserves circuit and voltage.
- `lesson.prompt` is the text to show. `step_done` turns true once the circuit has met
  every circuit and touch goal for half a second on a visible mat, and stays true.
  Six seconds later the next prompt arrives, unless `reflection` contains a spoken
  question. That question waits for `continue_lesson` with the current `step_id`.
  Stale or early Continue messages do nothing. `lesson_done` turns true after the
  final reflection is acknowledged. Speech is not recorded or analysed yet.
- A switch's `closed` comes from the piece: the learner swaps the closed switch piece
  (green) for the open one (cyan). A fingertip on a switch changes nothing.

## After changing the models

    make contract    # schemas and examples
    make sample      # the recorded run
