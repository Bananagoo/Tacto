# Tacto tech stack

Rewritten 21 Nov 2026 for the core lab. Rule: **reuse before build**. We write code only where a library would cost more than it saves.

Status key: **verified** = confirmed by running it on the demo laptop or by tests; **test** = must pass its check on our hardware before anyone builds on it.

## Shape

One Python server and one browser page on one macOS laptop, one WebSocket between them, Wi-Fi off.

```
LogiInsight camera ──colour frames──> server (Python) ──state, 15 a second──> lab UI (Chrome)
                                      flatten → classify → solve             draws the lab,
                                                         <──set_voltage──    wheel, mouse haptics
```

## Decisions

| Job | Decision | Reused from | Status and check |
|---|---|---|---|
| Camera frames | OpenCV `VideoCapture` on the device named `LVNext Camera`, 1080p, found by name | `opencv-python` | **verified** 21 Nov: about 30 fps on the demo laptop. **test**: mounted above the mat |
| Camera exposure | Manual exposure, set each time the camera is opened (`vision/exposure.py`); gain is the brightness knob. OpenCV cannot set it on macOS | [uvc-util](https://github.com/jtfrey/uvc-util) (MIT), pinned to a commit and built by `make camera-tool` into `server/vendor/` | **verified** 21 Nov by script on the demo laptop: auto clipped the paper and read 0 to 2 corner markers; manual at gain 0 read 4 with nothing clipped. **test**: after a replug, and with the camera above the mat |
| Mat position | Four ArUco corner markers (`DICT_4X4_50`, ids 0–3, 20 mm) → homography → flattened page | `cv2.aruco` | **verified** on rendered images with blur, dim light, tilt and a half turn. **test** on printed paper under venue lighting |
| Piece detection | One fixed patch per dot-to-dot segment of the flattened page; classify as empty, wire, battery, bulb, resistor or switch. Pieces carry no markers | OpenCV (HSV) for the baseline; classifier library to be chosen with the `reuse-first` skill | Baseline **verified** on rendered images (20 of 20 layouts in each of 10 views). **test** on real card under venue lighting. Trained classifier not built |
| Finger position | MediaPipe Hand Landmarker on our own colour frames; index tip mapped onto the mat through the corner-marker homography | `mediapipe` (Apache-2.0) | **verified** 21 Nov: about 26 ms a frame at 1080p. Gives position, not touch. **test**: fingertip within one segment on the printed mat |
| Circuit graph | `networkx`: connectivity, open loop, short and the shorted path | networkx | **verified** by unit tests |
| Circuit physics | ngspice through `InSpice` (DC operating point), behind `sim/solver.py`. Open loops and shorts are caught in the graph first | [InSpice](https://pypi.org/project/InSpice/) (GPL-3.0) + `brew install libngspice`; `NGSPICE_LIBRARY_PATH` in `.env` | **verified**: hand-worked tests for one bulb, series, parallel, short, bypassed bulb; about 1 ms a solve after a 0.4 s first load |
| Server and transport | FastAPI + uvicorn, one WebSocket, pydantic v2 models as the contract; JSON schema exported to `contract/` | FastAPI, pydantic | **verified** by tests and a live run |
| Lesson and mat content | YAML files in `lessons/` and `kit/mats/`, validated by pydantic | PyYAML | **verified** by tests |
| Printable mat | Script renders the A4 page (dots, corner markers, 50 mm check bar) to PDF from the mat file, so the print matches the reader's geometry | `cv2.aruco.generateImageMarker`, Pillow | **verified** by tests. **test**: printed and measured |
| Lab UI | Vite + React + TypeScript, Tailwind, zustand, `motion` | — | Owned by the UI team |
| Haptics | WebHID to the MX Master 4 through the Logi Bolt receiver: a preset tick looped at `pulse_hz`, a hard preset looped fast for the short buzz | [mx-master-4-webhid](https://github.com/mario-gutierrez/mx-master-4-webhid) (MIT); function numbers from the Solaar project | **verified** 21 Nov: speed and strength sliders both felt on the real mouse. Owned by the UI team |
| Tooling | `uv`, `ruff`, `pytest`; `pnpm`, `tsc`, `oxlint`, `prettier`; `make` | — | **verified** |

## Built ourselves, and why

- **Segment reading.** No library reads card pieces on a dot grid. The grid makes it one small classification per segment.
- **Lesson steps and switch taps.** A few lines of rules each.

## Hardware facts

Measured on the demo laptop on 21 Nov 2026 (`docs/hardware-log.md`) unless marked otherwise.

1. **The camera is the "Mac RGB stream edition".** It exposes one video device, `LVNext Camera`, in colour, at 640×480 up to 3840×2160, same field of view at every size. There is no near-infrared device on this unit.
2. **OpenCV's camera index order is not fixed** on macOS (it follows the devices' unique ids; an iPhone nearby shifts it). Find the camera by name; never hard-code an index.
3. **Auto-exposure washes out white paper on a dark desk.** The server switches the camera to manual exposure when it opens it (`make camera-tool` must have run). Mounting the camera above the mat so paper fills the frame is still wanted, for resolution.
4. **Do not leave the camera streaming between tests.** Logitech's docs warn it can overheat; the on-camera face AI makes this worse and we do not use it.
5. **Hand tracking is MediaPipe, not the Logi Hands Tracker app.** Per Logitech's docs, not confirmed on this laptop: the Hands Tracker app needs the near-infrared stream, publishes thumb and index tips on `ws://127.0.0.1:8765`, needs a four-touch calibration, and requires the colour stream opened as raw NV12 or YUY2 (not MJPG) so the infrared stream keeps its frame rate. None of that applies while we use MediaPipe on the colour stream.
6. **Haptics are preset waveforms, not a continuous motor.** The mouse reports 15 presets (0–14). There is no custom waveform. Strength (0–100) can be set over WebHID; it is stored on the mouse, so set it once, not per tick. "Current" is a short tick repeated at a rate the server sends.
7. **The mouse is driven through the Logi Bolt USB receiver** (046d:c548). WebHID needs Chrome or Edge and one click to connect.
8. **Everything is localhost-only.** The whole demo runs on the laptop that has the camera and the mouse.

## Not using

- Any LLM, speech or text-to-speech service (parked).
- A database (parked with the learner model).
- The LogiInsight SSH/AI link and the camera's face AI.
- Logi Hands Tracker and Logi Gaze Tracker.
- Markers on the pieces.

## Sources

- Logitech hackathon tools: https://logitech.github.io/hackathons/
- MediaPipe Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- InSpice: https://pypi.org/project/InSpice/
