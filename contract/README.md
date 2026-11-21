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
| `sample-states.jsonl` | A 22-second run, one state per line: empty mat, open loop, switch tap, voltage 6 → 9 → 6 V, series, mat hidden, parallel, short, resistor |

## Run the mock

    make mock

It replays `sample-states.jsonl` on `ws://localhost:8000/ws`, looping, with `seq`
and `t` counting up. It needs no camera, mouse or solver. It accepts
`set_voltage` and logs it, but a recording does not react to it.

## Set the mat by hand

    make manual      # then open http://localhost:8000/manual

The real lab with the camera replaced by a page: pick a tool and click between
two dots, or load a preset (open, one bulb, series, parallel, short). It runs
the real solver, reacts to `set_voltage`, and serves the same `/ws`, so the lab
UI can be put into any state on demand. It needs ngspice (`brew install libngspice`).
It runs the lesson in `lessons/circuits-101.yaml`; "Restart lesson" on the page
starts it again. With "Finger follows the pointer" on, resting the pointer on a
switch for half a second taps it, exactly as a fingertip does on the paper.

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
  last. Play `pulse_hz` ticks a second on the mouse; if `buzz` is true play one hard
  continuous buzz. Vibration is current, never voltage.
- `mat_visible: false` means the camera has lost the mat; pieces hold their last values.
- `lesson.prompt` is the text to show. `step_done` turns true once the circuit has met
  the step's goal for half a second, and stays true; about six seconds later the next
  step's prompt arrives. `lesson_done` turns true when the last step is done.
- On the camera a switch's `closed` comes from the piece: the learner swaps the closed
  switch piece (green) for the open one (cyan), and a fingertip on it changes nothing.
  On the hand-set mat (`make manual`) a fingertip resting on a switch for half a second
  still flips it, and must leave before it can flip it again.

## After changing the models

    make contract    # schemas and examples
    make sample      # the recorded run
