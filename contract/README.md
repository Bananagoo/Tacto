# The state contract

What the server and the lab UI say to each other. The Python models in
`server/tacto/contract.py` are the source; everything here is generated from
them. Changes need the vision owner's sign-off.

| File | What it is |
|---|---|
| `state.schema.json` | JSON schema of the one message the server sends, about 15 times a second |
| `set_voltage.schema.json` | JSON schema of the one message the browser sends |
| `example-state.json` | One state: a bulb on a closed loop at 6 V, a finger on the bulb |
| `example-set-voltage.json` | One browser message |
| `sample-states.jsonl` | A 22-second run, one state per line: empty mat, open loop, switch closed, voltage 6 → 9 → 6 V, series, mat hidden, parallel, short, resistor |

## Run the mock

    make mock

It replays `sample-states.jsonl` on `ws://localhost:8000/ws`, looping, with `seq`
and `t` counting up. It needs no camera, mouse or solver. It accepts
`set_voltage` and logs it, but a recording does not react to it.

## Reading a state

- Dots are `[col, row]`, origin top-left. `grid` gives the number of dots.
- Every piece lies between two neighbouring dots, `a` and `b`. Its `id` is that
  segment, `"c,r-c,r"` with the top-left dot first.
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
- `lesson.prompt` is the text to show. `step_done` turns true once the circuit has met
  the step's goal for half a second, and stays true; about six seconds later the next
  step's prompt arrives. `lesson_done` turns true when the last step is done.
- A switch's `closed` comes from the piece: the learner swaps the closed switch piece
  (green) for the open one (cyan). A fingertip on a switch changes nothing.

## After changing the models

    make contract    # schemas and examples
    make sample      # the recorded run
