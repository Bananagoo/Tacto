---
paths:
  - "server/tacto/vision/**"
  - "web/src/haptics/**"
  - "kit/**"
---

# Hardware facts (from the vendor docs, 21 Nov 2026, unless marked "our caution")

Links and the full list are in `docs/tech-stack.md`. These are the ones that break builds.

## LogiInsight camera

- Devices are named `LVNext Camera` (RGB, ~30 fps at 1920×1080) and `LVNext CPD Camera` (near-infrared, portrait, monochrome). Find them with the SDK's `camera_utils.py`; do not hard-code an index.
- **Open RGB as NV12 or YUY2, never MJPG, and open RGB before anything opens NIR.** With RGB as MJPG the NIR stream drops to about 1 fps, and the Hands Tracker lives on NIR. Raw 1080p needs a USB 3 port and cable.
- Set resolution before pixel format.
- The on-camera face AI overheats the camera after about 10 minutes and freezes video. We do not use it. Turn it off once with `set_ai_config(enable_face_detection=False, enable_face_mesh=False)`.
- macOS: the terminal running the server needs Camera permission.
- The SDK zip is not in this repo. Download it from the Logitech hackathon page into `server/vendor/` (gitignored).

## Logi Hands Tracker

- Separate app; publishes on `ws://127.0.0.1:8765`, one `hand_telemetry` message per frame (~30/s), one-way, localhost only.
- Only `thumb_tip` and `index_tip` per hand, 2D, normalised 0..1, **x mirrored, y bottom-up**, relative to a 1024×768 crop unless `camera_resolution` is set in its `config.json`.
- Map to the mat with the 4-touch calibration (learner touches each corner marker; fit a homography from tracker coordinates to mat coordinates). Do not derive the mapping from first principles.
- `handedness` labels can swap. Use the hand closest to the mat centre, or the one that is moving, not a fixed label.
- Smoothing is on by default (`alpha` 0.35). That adds lag; turn it down if the probe feels late.

## Reading the mat

- Markers: `cv2.aruco`, dictionary `DICT_4X4_50`, from stock `opencv-python` (`cv2.aruco.ArucoDetector`).
- Our caution: pen and inkjet inks are often faint or invisible in near-infrared. Read the mat from RGB only.
- A hand over the mat hides markers and wires. Keep the last known reading for anything occluded and smooth each segment's ink decision over several frames.
- Corner markers move only if someone bumps the camera or the mat. Cache the homography and refresh it when all four corners are visible.

## MX Master 4 haptics

- Preset waveforms only, indices 0–14 (names in `web/src/haptics/driver.ts`); the mouse itself reports 15 presets. There is no continuous vibration: loop a preset instead. Strength (0–100) can be set from code with the `webhid` driver's `setStrength`; it is a setting stored on the mouse, so do not change it on every tick. The plugin driver cannot set it.
- Plugin driver: `wss://local.jmw.nz:41443/ws`, send one byte (the waveform index). Needs Logi Options+ and the Haptic Web plugin installed. `local.jmw.nz` must resolve to 127.0.0.1; the docs do not say how it does, so add it to `/etc/hosts` for the demo.
- WebHID driver: Chrome or Edge, needs a click to call `connect()`. Effect ids 0–14; not confirmed to be in the same order as the plugin's indices.
- "Current" is a short tick repeated at `pulse_hz`. The fastest usable rate is a measured constant (`MAX_PULSE_HZ`), not a guess.
- All haptic calls go through `HapticsDriver`. Never call the plugin or WebHID from anywhere else.
