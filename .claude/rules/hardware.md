---
paths:
  - "server/tacto/vision/**"
  - "server/tacto_bench/**"
  - "scripts/**"
  - "kit/**"
---

# Hardware facts

Measured on the demo laptop on 21 Nov 2026 unless marked. The full list is in `docs/tech-stack.md`; results go in `docs/hardware-log.md`.

## LogiInsight camera

- This unit is the "Mac RGB stream edition": one video device, `LVNext Camera`, colour only, about 30 fps at 1920×1080, up to 3840×2160 with the same field of view. No near-infrared device.
- Find the camera by name (`vision/camera.py: list_cameras`). OpenCV's index order on macOS follows device ids and shifts when an iPhone is near; never hard-code an index.
- Auto-exposure washes out white paper against a dark desk. Mount the camera above the mat so paper fills most of the frame.
- Do not leave the camera streaming between tests; it can overheat. We do not use the on-camera face AI or the SSH link. Never ask for or read the credentials on the kit card.
- macOS: the terminal running the server needs Camera permission.

## Hand tracking

- MediaPipe Hand Landmarker on our own colour frames (`vision/hands.py`), about 26 ms a frame. The model file lives in `server/vendor/` (gitignored).
- It gives 21 landmark positions, not touch. A fingertip over a segment counts as touching it.
- Handedness labels can swap. Use the hand pointing nearest the middle of the frame, not a fixed label.
- Per Logitech's docs, not confirmed on this laptop: the Logi Hands Tracker app needs the near-infrared stream and a raw NV12/YUY2 colour stream, publishes on `ws://127.0.0.1:8765`, and needs a four-touch calibration. We do not use it.

## Reading the mat

- Corner markers: `cv2.aruco`, dictionary `DICT_4X4_50`, ids 0–3 clockwise from the top-left, 20 mm. The pieces carry no markers.
- The printed mat must come from `make kit`, so the print geometry matches the reader's exactly. Print at 100% and check the 50 mm bar.
- A hand over the mat hides corners and pieces. Keep the last homography when a corner is hidden, and keep the last stable class of any segment under the hand (padded MediaPipe landmarks are the mask).
- A segment changes class only after N consecutive frames agree.

## MX Master 4 haptics (UI team's lane; facts only)

- 15 preset waveforms (0–14) and nothing else; no continuous vibration and no custom waveform. A steady pulse is a preset looped at a rate.
- Strength (0–100) can be set over WebHID. It is stored on the mouse: set it once, not per tick.
- Driven through the Logi Bolt USB receiver; WebHID needs Chrome or Edge and one click to connect.
- The server sends `touch.pulse_hz` (current) and `touch.buzz` (short). The browser only plays them.
