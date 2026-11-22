# Lessons

One YAML file per lesson. A lesson is a fixed list of steps; changing wording never needs a code change. The wording belongs to the lesson author.

`circuits-101.yaml` is the lesson for the demo. Its prompts are placeholders.

## Shape of a file

```yaml
id: circuits-101
title: Circuits 101
linger_seconds: 6          # how long a finished step stays on screen before the next prompt

steps:
  - id: close_the_loop     # unique within the file
    prompt: "Close the gap with a wire. Rest a finger on any piece: the pulse in the mouse is the current."
    done_when: { status: working, lit_bulbs: 1 }
    linger_seconds: 10     # optional, overrides the lesson's for this step
```

## `done_when`

Every condition given must hold; leave out the ones that do not matter.

| Condition | Values | Meaning |
|---|---|---|
| `status` | `working`, `open`, `shorted` | The circuit as a whole |
| `batteries` | a number | Batteries on the mat |
| `bulbs` | a number | Bulbs on the mat |
| `lit_bulbs` | a number | Bulbs carrying current |
| `arrangement` | `single`, `series`, `parallel` | How the lit bulbs are connected |

## How a step runs

The prompt is shown. When the circuit has met `done_when` for half a second, the step is done and stays done. After the linger time the next step's prompt appears. The last step, once done, ends the lesson. Nothing is asked of the learner except the circuit: a prompt may still say "what do you expect?".

## Writing prompts

- One or two short sentences, readable from two metres away.
- The pulse in the mouse is **current**. The wheel is **voltage**. Never swap them.
- A step's goal must not already be true on an empty mat, or on the circuit that finished the step before it.

## Check your edit

```
make check-server
```

A file with a mistake fails with a message that names the file and the field. To try the lesson: `make dev`, build on the mat, and watch `localhost:5173/devtools/#state`.
