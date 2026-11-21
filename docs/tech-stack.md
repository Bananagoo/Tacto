# Tacto tech stack

Decided 21 Nov 2026. Rule: **reuse before build**. We write code only where a library would cost more than it saves, and each such case is listed under "Built ourselves".

Status key: **verified** = confirmed in the vendor's docs or by running it; **test** = must pass its check on our hardware before anyone builds on it.

Not yet installed or tried: `@ricky0123/vad-web`, `pupil-apriltags`, `@xyflow/react`, the three.js packages, and the OpenAI-compatible endpoints for Together and OpenRouter. They are named from general knowledge, so confirm each one when you first reach for it (the `reuse-first` skill does this).

## Shape

Two processes on one laptop, one WebSocket between them.

```
LogiInsight cam ──RGB──> server (Python)  ──state @ ~15 Hz──>  web (browser, Chrome)
Logi Hands Tracker ─ws─>   vision → circuit → solver → tutor     bench view, concept map
                                                  <──events──   wheel, answers, mic audio
                           Together / OpenRouter (keys stay here)   └─> MX Master 4 haptics
```

- `server/` owns the world state: what is on the mat, the solved circuit, where the finger is, the lesson and learner model. It is the only place API keys live.
- `web/` renders the state and owns everything the browser is best at: drawing, wheel events, microphone, haptics.
- Nothing in the real-time loop (camera → solver → screen → haptics) touches the network.

## Decisions

| Job | Decision | Reused from | Fallback | Status and check |
|---|---|---|---|---|
| Camera frames | OpenCV `VideoCapture` on the `LVNext Camera` RGB device, 1080p | LogiInsight Python SDK helpers (`camera_utils.py`) for device discovery | Any UVC webcam | **test**: frames arrive with the camera mounted over the desk |
| Mat and part detection | ArUco markers (`DICT_4X4_50`): 4 corners → homography, 1 marker per part | `cv2.aruco` in stock `opencv-python` | AprilTag via `pupil-apriltags` | **verified**: generate + detect ran on OpenCV 5.1 (Linux); **test** under venue lighting |
| Wire detection | Sample each dot-to-dot segment in the flattened image and threshold ink against paper | OpenCV (warp, adaptive threshold) | Printed wire strips with markers | **test**: 10 layouts read correctly |
| Finger position | MediaPipe Hand Landmarker on our own RGB frames; the index tip is mapped onto the mat through the corner-marker homography, so no touch calibration is needed | `mediapipe` (Apache-2.0) | — | **verified** 21 Nov: about 26 ms a frame at 1080p on the demo laptop. This unit has no near-infrared stream, so the Logi Hands Tracker app is not used. **test**: fingertip within one grid cell on the printed mat |
| Circuit graph | `networkx` for connectivity, open-loop and short detection | networkx | — | verified by unit tests |
| Circuit physics | ngspice through `InSpice` (operating-point analysis), behind one `solve()` function in `sim/solver.py`; open loops and shorts are caught by networkx before the engine is called | [InSpice](https://pypi.org/project/InSpice/) (GPL-3.0, maintained fork of PySpice) + `brew install libngspice`, with `NGSPICE_LIBRARY_PATH` set in `.env` | Own modified nodal analysis in NumPy (about 80 lines) behind the same function | **verified**: one bulb and two in series solved correctly on macOS arm64 with ngspice 47, 0.22 ms per solve; unit tests against hand-worked answers still to write |
| Server and transport | FastAPI + uvicorn, one WebSocket, pydantic v2 models as the contract | FastAPI, pydantic | — | verified in the skeleton |
| Web app | Vite + React + TypeScript, Tailwind, zustand store | Vite `react-ts` template | — | verified build in the skeleton |
| Bench view | SVG parts in React, glow and motion with `motion` | `motion`; `@wokwi/elements` (MIT) as reference art for resistor and switch | Static images | **test**: glow follows the solver within 250 ms |
| 3D parts (stretch) | `@react-three/fiber` + `@react-three/drei` | three.js ecosystem | Stay 2D | not started |
| Concept map | Six fixed nodes in plain SVG | — | `@xyflow/react` if we want drag and zoom | — |
| Haptics | One `HapticsDriver` interface; default is the Haptic Web plugin over `wss://local.jmw.nz:41443/ws` (send one byte = waveform index) | [HapticWebPlugin](https://github.com/fallstop/HapticWebPlugin) (MIT) | [mx-master-4-webhid](https://github.com/mario-gutierrez/mx-master-4-webhid) (MIT, `triggerHaptic(0..14)`), then the C# Actions SDK | **test**: pulse fires from our page; measure max repeat rate and latency. 2026-11-21: `webhid` pulse confirmed on the real mouse; plugin untested (Logi Options+ not installed on that laptop). Dev test page: `web/src/haptics/test.html` (`make web`, open `/src/haptics/test.html`); it uses the same `HapticsDriver` classes as the app. `HapticsDriver` gained `isConnected` and `close()`, and `playRaw` now rejects indices outside 0 to 15 |
| Scroll wheel | Browser `wheel` events, accumulated into voltage steps | Browser | Up/down keys | **test**: ticks arrive with smooth-scroll on and off |
| Speech in | Silero VAD in the browser cuts one utterance → server → Together `openai/whisper-large-v3` | `@ricky0123/vad-web`, Together SDK | Two on-screen buttons (always present) | **test**: prediction transcribed in ~1 s in a noisy hall |
| Answer matching | Keyword match on the closed answer set first; LLM only when no keyword hits | — | Buttons | unit tests |
| Tutor voice | Scripted lines pre-generated once with Together `hexgrad/Kokoro-82M` and committed as audio files; live hints generated on demand and cached | Together TTS | Browser `speechSynthesis` | **test**: playback starts within 1 s |
| Tutor wording | `Qwen/Qwen3.5-9B` on Together, JSON output validated by pydantic; given the circuit and learner state as text | `openai` SDK pointed at Together's and OpenRouter's OpenAI-compatible endpoints | Pre-written hint ladder in the lesson file | **test**: one sentence, never states the answer |
| Freehand sketches (stretch) | Same 9B model with an image, or a vision model through OpenRouter, fixed output schema | OpenRouter | Stay on the grid | 8 of 10 sketches parsed |
| Learner model | Per-concept mastery (shaky/solid) + the zone score rule from the concept brief | — | — | unit tests |
| Lesson content | YAML files in `lessons/`, validated by pydantic | PyYAML | — | loads at startup |
| Data | SQLite file (`server/data/tacto.db`) through SQLModel: lessons, the concept graph, learners (a nickname), mastery and prediction attempts. Written on lesson events only, never per frame | `sqlmodel` | — | verified by unit tests on an in-memory database |
| Mat reading | The mat is a fixed printed circuit with drawable lines and tile slots (`kit/mats/`). Four corner ArUco markers flatten the page; each tile carries a marker; a drawn line is an ink test along its segment | `cv2.aruco`, OpenCV | — | verified on rendered and degraded images; **test** on the printed kit under venue lighting |
| Paper kit | Script renders the A4 mat and parts sheet to PDF | `cv2.aruco.generateImageMarker`, Pillow | — | **test**: printed kit detected by the camera |
| Tooling | `uv`, `ruff`, `pytest`; `pnpm`, `tsc`, `oxlint`, `prettier`; `make` | — | — | verified in the skeleton |

## Built ourselves, and why

- **Wire reading.** No library reads pen lines on a dot grid. The grid makes it a per-segment darkness test.
- **Tutor state machine and learner model.** Two small rules the team can state in one sentence. Knowledge-tracing libraries such as pyBKT fit parameters from large logs, which we do not have.
- **Concept map.** Six fixed nodes do not justify a graph library.

## Facts that change the build

From the vendor docs unless marked as our own caution.

1. **RGB and NIR together need raw RGB.** The Hands Tracker uses the NIR stream (`LVNext CPD Camera`). If we open RGB as MJPG at the same time, NIR drops to about 1 fps. Open RGB as NV12 or YUY2 (needs a USB 3 port and cable), and open RGB first.
2. **The camera's face AI overheats it.** Continuous on-camera AI for 10+ minutes can freeze the video. We do not use face data, so turn it off with `set_ai_config(enable_face_detection=False, enable_face_mesh=False)`.
3. **Hands Tracker publishes only thumb tip and index tip, in 2D**, normalised, x mirrored, y bottom-up, inside a 1024×768 crop by default. Do not hand-derive the mapping. Calibrate by touching the four corner markers and fitting a homography from tracker coordinates straight to mat coordinates.
4. **Our caution, not from the docs: pen and inkjet inks are often faint or invisible in near-infrared.** So the mat is always read from RGB, and the 4-touch calibration avoids depending on printed markers showing up in the NIR frame. Worth a two-minute look at the NIR preview with our pen and printout.
5. **One camera cannot watch the desk and the face.** The brief's "is the student facing the page" signal is dropped from the MVP. The zone uses desk signals only: hand activity, circuit edits, prediction results, idle time. Stretch: the laptop's own webcam with MediaPipe Face Landmarker in the browser.
6. **Haptics are preset waveforms, not a continuous motor.** 15 presets (0–14, read from the mouse on 21 Nov), named in the plugin docs (`sharp_collision`, `subtle_collision`, `knock`, `square`, …). Strength (0–100) is not in Logitech's docs but can be set over WebHID (`setStrength` in `web/src/haptics/driver.ts`, function numbers from the Solaar project). "Current" is a short tick repeated at a rate set by the solver; the usable maximum rate has to be measured.
7. **The Haptic Web plugin is a Logi Actions SDK plugin (so it runs inside Logi Options+) served at `https://local.jmw.nz:41443`, bound to 127.0.0.1.** The docs do not say how that hostname resolves; we assume public DNS. To be safe on venue Wi-Fi, add `127.0.0.1 local.jmw.nz` to `/etc/hosts`. WebHID needs Chrome or Edge and a user click to connect.
8. **Hands Tracker and Haptic plugin are localhost-only.** The whole demo runs on the laptop that has the camera and the mouse.

## Models and cost

| Use | Model | Price | When it runs |
|---|---|---|---|
| Hints, answer fallback | `Qwen/Qwen3.5-9B` (Together) | $0.17 in / $0.25 out per 1M tokens | Only when the learner is stuck or an answer matches no keyword |
| Speech to text | `openai/whisper-large-v3` (Together) | $0.0015 per audio minute | One short clip per prediction |
| Tutor voice | `hexgrad/Kokoro-82M` (Together) | $4 per 1M characters | Once at build time for scripted lines |
| Sketch reading (stretch) | 9B model with image, or OpenRouter vision model | — | Never in the main loop |

Prices read from Together's serverless catalog on 21 Nov 2026. The frugality line for AXA: the camera image becomes a ten-line text netlist with classic image processing, a 9B model writes one sentence from it, and a full lesson costs a fraction of a cent. Log tokens per lesson so we can show the number.

## Not using

- **LangChain or an agent framework.** One prompt, one JSON reply.
- **A database server.** Data lives in a local SQLite file (decided 21 Nov; the row is added to the table above when the dependency lands).
- **The LogiInsight SSH/AI link**, except once to switch the face AI off.
- **Logi Gaze Tracker.** The camera is pointed at the desk.
- **CircuitJS1 as the main simulator.** Driving an iframe from camera input is harder than solving the circuit.

## Sources

- Logitech hackathon tools: https://logitech.github.io/hackathons/
- LogiInsight SDK quick start: https://logitech.github.io/hackathons/logiinsight/
- Logi Hands Tracker: https://logitech.github.io/hackathons/logi-hands-tracker/
- Haptic Web plugin API: https://haptics.jmw.nz/api
- Together models and prices: https://docs.together.ai/docs/serverless/models
- Together speech: https://docs.together.ai/docs/speech-to-text, https://docs.together.ai/docs/text-to-speech
- MediaPipe Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- Wokwi elements: https://github.com/wokwi/wokwi-elements
- CircuitJS1: https://github.com/pfalstad/circuitjs1
