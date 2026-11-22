# Lessons

One YAML file per lesson. A lesson is a fixed list of steps; changing wording never needs a code change. The wording belongs to the lesson author.

`circuits-101.yaml` is the lesson the lab runs: the short demo, three steps and one spoken
question (close the loop; feel the current and raise the voltage; parallel). See
`docs/lab-flow.md`. `circuits-101-full.yaml` is the full six-step version (open switch,
closed switch, feel current, raise voltage, series, parallel), kept for reference and for
the lesson engine's tests.

The app starts in **Tinker**, where the circuit and wheel work freely and no lesson
goals run. Choosing **Lab** starts at step one and 3 V. Returning to Tinker preserves
the circuit and voltage; entering Lab again starts a fresh lesson.

## Shape of a file

```yaml
id: circuits-101
title: Circuits 101
linger_seconds: 6          # how long a finished step stays on screen before the next prompt

steps:
  - id: close_the_loop     # unique within the file
    prompt: "Swap in the closed switch. Watch the bulb."
    done_when: { status: working, lit_bulbs: 1, switch_closed: true }
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
| `switch_closed` | `true`, `false` | At least one switch exists and every switch has that state |
| `min_voltage` | 0–9 | Battery voltage is at least this many volts |
| `touching` | a piece type, or `current` | Finger over that type (or any piece), carrying at least 0.005 A; shorts do not count |

## How a step runs

The action is done once all circuit and touch conditions have held for half a second
on a visible mat. Losing the mat or lifting the finger before that resets the timer.
Camera tracking estimates a finger over a piece; it cannot measure contact.

Steps without a reflection advance after `linger_seconds`. An optional `reflection`
string asks the student to explain out loud after completing the action. It stays
until **Continue**, or **Finish lab** on the final step. Answers are not recorded,
transcribed or scored. There is no deadline on a spoken reflection.

**Restart** or **R** in Lab restores step one and 3 V and clears reflection progress.
It does not move the cards: restore one bulb, the bottom wire and the switch slot.
Keyboard shortcuts ignore text fields and modifier keys.

## Three-minute pitch

Aim for 90 seconds hands-on, leaving 90 seconds for the problem, technology and close.
These are rehearsal targets, not student time limits. Prearrange the loop with a
switch slot and two side-branch wires, leaving the branch bulb slot empty. Have both
switch cards and the second bulb ready. Keep one hand on the mouse and point at the
cards with the other.

| Step | Target | Presenter line |
|---|---|---|
| Open switch | 10 s | The battery is there, but current needs a complete path. |
| Closed switch | 10 s | The camera reads your change, and the simulated circuit responds. |
| Feel current | 10 s | The pulse represents current through the piece you are touching. |
| Raise 3 → 6 V | 15 s | The wheel controls voltage. Through this bulb, more voltage means more current. |
| Series | 20 s | More resistance at the same voltage means less current through both bulbs. |
| Parallel | 25 s | The battery supplies both branches: twice either equal bulb's current. |

Use the six-second success pauses for the presenter lines. On the last three steps,
let the learner reflect, then Continue. Keep voltage at 6 V through series and parallel.
Expected rates are about 1.5 Hz at 3 V with one bulb, 3 Hz at 6 V, 1.5 Hz in series,
and 3 Hz per parallel bulb versus 6 Hz at the battery. Above 6 V the battery pulse
reaches the UI's 6 Hz cap, obscuring the comparison. Rehearse the rearrangement and
pulse contrast on the real hardware.

## Writing prompts

- One or two short sentences, readable from two metres away.
- The pulse in the mouse is **current**. The wheel is **voltage**. Never swap them.
- A step's goal must not already be true on an empty mat, or on the circuit that finished the step before it.

## Check your edit

```
make check-server
```

A file with a mistake fails with a message that names the file and the field. To try the lesson: `make dev`, build on the mat, and watch the lab, or the setup check's reading at `localhost:5173/devtools/#setup`.

## A reflection as a funnel

A step's `reflection` can be one question, as above, or a funnel: an open question, a narrower one, a choice between two, and then the lab states the idea and asks for an action on the mat. A learner who answers the first question well never hears the others. Every line the lab says is written here, so the wording can be edited without touching code. The plan behind it is `docs/voice-reflections-plan.md`.

```yaml
reflection:
  target_idea: "Two bulbs in a row resist more, so the same battery drives less current."
  confirmation: "Yes. Two bulbs in a row resist more, so the same battery pushes less current."
  misconceptions:                # wrong ideas worth naming; tags are lower_case_words
    - tag: current_used_up
      description: "Thinks the first bulb uses some of the current up."
  levels:                        # one to three, from open to narrow
    - question: "Why did adding a second bulb make the pulse slower?"
      correct_examples:          # two to five right answers, said as a learner would
        - "theres more resistance now so less current gets through"
        - "two bulbs are harder to push through so the current drops"
      confirmation: "Exactly."   # optional; the funnel's is used when left out
  exit:
    line: "Two bulbs in a row resist more. Touch the other bulb: the pulse is the same there."
    then:                        # goals to meet one after another
      - { touching: bulb, different_piece: true }
    timeout_seconds: 20          # optional; the lesson moves on after this regardless
```

An exit goal takes every `done_when` condition, plus:

| Condition | Meaning |
|---|---|
| `max_voltage` | Battery voltage is at most this many volts (also usable in `done_when`) |
| `different_piece: true` | The touched piece is not the one being touched when the step was finished: "touch the other bulb" |
