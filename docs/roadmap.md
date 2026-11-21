# MVP roadmap

**Goal.** A judge builds a paper circuit, sees the bulb light on screen and feels the current in the mouse, inside a three-minute demo.

Each phase has a gate. Do not start the next phase until the gate passes or the fallback is chosen. Run `/gate <phase>` to check where we are.

## Phase 1: prove each piece (in parallel)

| Lane | Test | Done when | Fallback |
|---|---|---|---|
| Sim and haptics | Fire a pulse from the dev harness with the `plugin` driver, then `webhid`. Feel waveforms 0–14. Find the fastest tick rate that still feels like separate ticks | A pulse fires on command; `WAVEFORM` table and `MAX_PULSE_HZ` are set from what was felt | Other driver; then C# Actions SDK |
| Sim and haptics | Circuit solver for one bulb, two in series, two in parallel | Unit tests match hand-worked answers | — |
| Vision | Mount the camera over the desk, open RGB as NV12 or YUY2, detect the four corner markers and flatten the mat | One printed mat reads correctly under venue lighting; 20 frames saved to `server/fixtures/` | Any UVC webcam |
| Vision | Hands Tracker running at the same time as our RGB capture; 4-touch calibration | Fingertip lands within one grid cell; NIR still ~30 fps | MediaPipe Hand Landmarker on the RGB frame |
| Vision | `kit/make_kit.py` renders mat and parts to PDF; print and cut one set | Camera test runs on the real kit | — |
| Front end | Bench view draws parts from a `State`; bulb glow follows `brightness` | Mock state renders; wheel changes the glow | — |
| Lesson | Write three challenges (light the bulb, series, parallel) in `lessons/circuits-101.yaml`: prompt, prediction choices, right answer, hint ladder | File loads and validates | — |
| Lesson | Ask Logitech's booth: does a learning tool qualify, and what do they score on | Answer written in `docs/demo-script.md` | — |

**Gate 1:** all tests pass or a fallback is chosen and written into `docs/tech-stack.md`.

## Phase 2: core loop

- Mat reading feeds the solver; the solver feeds the bench view.
- Scroll wheel sets the voltage.

**Gate 2:** a paper battery, a bulb and two drawn wires light the bulb on screen, and the wheel changes its brightness. Works in `replay` and in `camera` mode.

## Phase 3: feel

- Fingertip on a wire pulses the mouse at a rate set by the current there.
- Lifting a part stops the pulse; a short gives the `short` pattern.

**Gate 3:** touching a wire gives a pulse, raising the voltage quickens it, lifting a part stops it.

## Phase 4: tutor

- Zone of productive learning: running score, +1 correct prediction, −1 repeated error or 30 s idle, state change at ±3. One tutor response per state.
- Learner map: six concepts, shaky or solid, shown on screen, used to pick the next challenge.
- Voice: spoken prompts and spoken predictions; buttons always available.

**Gate 4:** three challenges run end to end; the tutor steps down once and up once in a run.

## Phase 5: rehearse

- Fix lighting and camera mount. Turn the camera's face AI off. Add `127.0.0.1 local.jmw.nz` to `/etc/hosts` if using the plugin.
- Record a backup video.

**Gate 5:** three clean run-throughs inside three minutes, one of them with Wi-Fi off.

## Should have, after gate 4

Concept map animation, zone gauge, the "break it" and "turn it up" challenges, token-cost readout for the AXA pitch.

## Stretch

3D parts, freehand sketches read by a vision model, a second language for the tutor's voice, laptop-webcam "looked away" signal.

## Not now

Emotion detection, student accounts with logins, teacher dashboard, any chat interface.

Moved into scope on 21 Nov 2026 (see `docs/superpowers/specs/2026-11-21-tacto-platform-design.md`): a local database for lesson content, a learner's nickname and their learning graph, and progress saved between sessions.
