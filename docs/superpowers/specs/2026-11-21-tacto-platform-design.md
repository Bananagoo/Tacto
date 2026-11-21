# Tacto platform design

Agreed with the project owner on 21 Nov 2026. This is the design the build plans argue from.

## What we are building

The real product for one lesson, "Circuits 101", built so that a second lesson is new content and not new code. A learner places paper parts on a printed mat and draws wires. A camera above the desk reads the mat. The circuit runs on screen. The MX Master 4 is the instrument: the wheel sets voltage, vibration is current. A tutor asks for a prediction, lets the learner test it, then explains.

The only deliverable that matters is a three-minute demo a judge runs by hand, on one laptop, with Wi-Fi off.

## The lesson (from the team's lesson plan)

| Stage | Learner does | What happens | Teaches |
|---|---|---|---|
| Setup | Traces the wires of an open circuit | Bulb A is off, the mouse is silent | No loop, no current |
| 1. Close the loop | Draws the missing line, rests a finger on any wire | Bulb A lights, steady pulse | Current flows only in a closed loop |
| 2. Second bulb in series | Predicts, then places bulb B over a wire and slides a finger before, between and after the bulbs | Both bulbs equally dim; pulse rate halves and is the same everywhere | Current is the same everywhere in a loop; series resistances add |
| 3. Parallel | Predicts, then moves bulb B to a side branch | Each bulb at full brightness; each branch pulses at half the battery wire's rate | Each branch gets the full push |
| 4. Short | Draws a line across the circuit | Both bulbs go out, the battery wire glows orange, the mouse buzzes hard on the shorted path and is silent elsewhere | Current takes the easiest path |

Known wrong predictions to answer directly: "the first bulb is brighter because it uses up the current", "both stay as bright because the current is the same" (stage 2), and "both get dimmer because the current splits" (stage 3).

Open content question, owned by the lesson author: the repo rule is "predict before every test", but only stages 2 and 3 ask for a prediction. The schema makes a prediction optional per step so either answer works.

## Approaches considered

**Where lesson logic lives**

1. Hard-code the five stages in Python. Fastest today; a second lesson means new code.
2. **Lessons as data, one generic engine (chosen).** A lesson is an ordered list of steps; each step declares its goal circuit, optional prediction, what to observe, the explanation and hints. Slightly more design up front, and a second lesson is a YAML file.
3. A general workflow or rules engine. Far more than five linear steps need.

**Where data lives**

1. **SQLite through SQLModel (chosen).** One file, no server, works offline, models in the same style as the wire contract, and a later move to Postgres is a connection string.
2. Postgres. Real multi-user, but needs Docker or a network on the demo laptop.
3. A graph database for the learning graph. A whole new system for six concepts.

**Where test tooling lives**

1. Leave tooling inside the product packages behind flags. Least work; the product ships code it never runs and the boundary erodes.
2. **Separate package and separate page, with an automated boundary check (chosen).** Tooling may import the product; the product may never import tooling.
3. A separate repository. Cleanest wall, but tooling would drift from the code it tests.

## Hardware facts this design rests on

All checked on the demo laptop on 21 Nov 2026 (`docs/hardware-log.md`).

- The camera exposes one video stream, RGB, at 1920×1080 or 3840×2160, about 30 fps. There is no near-infrared stream on this unit and no wider field of view in software.
- Fingertip tracking is MediaPipe Hand Landmarker on our own frames (about 26 ms a frame). It gives position, not touch.
- The mouse plays 15 preset waveforms (0–14) and nothing else. A steady click is a preset looped at a chosen rate; strength (0–100) can be set over WebHID. It works through the Logi Bolt receiver.
- The circuit solver is ngspice through InSpice; open loops and shorts must be caught before the solver is called.

## Structure

### Product and tooling are separate

| | Product | Tooling |
|---|---|---|
| Server | `server/tacto/` | `server/tacto_bench/` |
| Web | `web/src/`, entry `web/index.html` | `web/devtools/`, entry `web/devtools/index.html` |
| Tests | `server/tests/` | `server/tests/bench/` |
| Run | `make dev` | `make bench` |

One-off hardware probes stay in `scripts/`. `server/tests/test_boundaries.py` fails if anything under `server/tacto/` imports `tacto_bench`, or anything under `web/src/` imports from `web/devtools/`. The production web build has a single entry, so tooling pages are never in the product bundle.

### Server modules

Each module has one job and meets the others through plain data, never through each other's internals.

| Module | Job | Depends on |
|---|---|---|
| `contract.py` | Every message on the wire. Changes are additive | — |
| `world.py` | The `World` interface the app serves: `state()` and `handle(message)` | contract |
| `app.py` | `create_app(make_world)`: the WebSocket and HTTP routes | world |
| `vision/` | Camera frames → parts, wires, fingertip in mat coordinates | — |
| `sim/` | Parts and wires → solved circuit; current → pulse rate | contract |
| `lessons/` | The lesson models and the engine that walks any lesson's steps | contract |
| `learner/` | Mastery per concept, the zone rule, the learning graph | — |
| `store/` | Database access behind small repository interfaces | lessons, learner |
| `session.py` | One learner's loop: source → sim → lesson engine → `State`. Implements `World` | all of the above |
| `main.py` | Reads configuration and builds the app | app, session |

The existing `tutor/` package becomes the home of spoken output only (hint wording, speech in, tutor audio), which arrives in the last wave. Lesson flow moves to `lessons/` and the learner model to `learner/`, because they are different jobs with different reasons to change.

### The real-time loop

Camera → mat reading → solver → `State` → screen and haptics. Nothing in it touches the network or the database. The database is written only on lesson events (an answer, a step completed).

### Lessons as data

```yaml
id: circuits-101
concepts: [closed_loop, current, voltage, resistance, series, parallel]
steps:
  - id: series
    teaches: [current, series]
    build:
      say: "Place the second bulb on the wire."
      done_when: { status: closed, bulbs: 2, topology: series }
    predict:            # optional
      say: "What will happen to the first bulb?"
      choices: { dimmer: [dimmer, darker], same: [same], brighter: [brighter] }
      answer: dimmer
      misconceptions:
        same: "Feel the pulse: it slowed down, so less current is flowing."
    observe:
      say: "Slide your finger along the loop, before and after each bulb."
    explain:
      say: "The current is the same all the way round, and two bulbs let less through."
    hints: ["...", "...", "..."]
```

`done_when` is a small closed set of circuit conditions (status, number of bulbs, topology), checked by the engine against the solved circuit. YAML in `lessons/` is the authoring format; at startup it is validated and loaded into the database, and the engine reads lessons through the store.

### Data model

| Table | Holds |
|---|---|
| `lesson`, `lesson_step` | Lesson content, steps in order, step body as validated JSON |
| `concept`, `concept_prerequisite` | The learning graph's nodes and edges |
| `learner` | A nickname. No login, no personal details |
| `mastery` | Per learner and concept: unseen, shaky or solid, with counts |
| `attempt` | One row per prediction: learner, step, choice, correct, when |

Nothing from the camera or microphone is stored.

### Web

`web/src/` holds the product: the bench view (SVG drawn from `State`), the tutor panel (prompt and prediction buttons, always visible as text), the concept map, haptics and input (wheel → voltage). All server data comes through the one store. `web/devtools/` holds the dev harness, the camera bench and the haptics page.

### Contract additions (additive only)

- `Tutor`: lesson id, step index and step count, so the screen can show progress.
- `Probe`: a way to ask for the continuous buzz of a short (a fast looped preset), separate from the pulse that means current.
- `Wire`: a flag for an overloaded wire, so the screen can draw it orange.

Exact field names are settled in the build plans and changed in `contract.py` and `contract.ts` together.

## Build order

Each wave ends with `make check` passing and a review by the project owner.

1. **Restructure.** Move tooling out of the product, add the boundary test. No new behaviour.
2. **Parallel wave, no hardware.** Simulation; store and lesson content; lesson engine and learner model; bench view and tutor panel.
3. **Integration.** The session loop replaces the mock; mat and wire reading feed it; replay mode from recorded frames.
4. **Live hardware.** Camera, fingertip, haptics for all five stages; then voice.

## Out of scope

Logins and accounts, a teacher dashboard, emotion detection, any chat interface, cloud sync, more than one lesson's content.

## Risks

- **Mat reading under venue lighting.** The camera picture is washed out under the hall's lights. Mitigation: replay mode from recorded frames, and a manual exposure check early.
- **Touch is inferred from position.** A fingertip held still over a wire counts as touching it.
- **ngspice on teammates' machines.** Each needs `brew install libngspice`; solver tests fail with a clear message without it.
- **Unpushed teammate work** on the paper kit. The vision lane is planned last so it can build on what they push.
