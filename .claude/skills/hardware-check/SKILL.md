---
name: hardware-check
description: Walk a teammate through one hardware de-risk test and record the result. Use when the user runs /hardware-check, or says they have the mouse or camera in hand and want to test it.
argument-hint: "[mouse | camera | hands | kit | voice]"
disable-model-invocation: true
---

Run the phase 1 test for **$ARGUMENTS** with the person who has the device. You cannot see the desk or feel the mouse: you give one step at a time, they tell you what happened, and you write it down.

Read `.claude/rules/hardware.md` first. Then follow the matching section. Ask for the result of each step before giving the next. If a step fails twice, switch to the fallback in `docs/tech-stack.md` instead of debugging for more than fifteen minutes.

## mouse

1. `make dev`, open http://localhost:5173 in Chrome.
2. Driver `plugin`: is Logi Options+ running and the Haptic Web plugin installed? Click Connect. If it errors, check that `local.jmw.nz` resolves (`ping -c1 local.jmw.nz`); if not, suggest adding `127.0.0.1 local.jmw.nz` to `/etc/hosts`.
3. Press buttons 0–15. For each, ask for two or three words on how it feels (short tick, double tap, long buzz).
4. Repeat with driver `webhid`. Note whether the ids feel like the same waveforms as the plugin's.
5. Pick with them: the shortest, cleanest tick for `tick`; something harsh for `short`. Update `WAVEFORM` in `web/src/haptics/driver.ts`.
6. Tick rate: scroll the wheel up in the harness so the pulse rate climbs. At what rate do ticks blur together? Set `MAX_PULSE_HZ` in `web/src/haptics/usePulse.ts` just below that.
7. Wheel: does one notch change the voltage by one step? Try with smooth scrolling on and off; adjust `WHEEL_UNITS_PER_STEP` in `web/src/App.tsx`.

## camera

1. Camera mounted looking straight down at the mat, on a USB 3 port.
2. Write (or run) a script in `server/tacto/vision/` that finds `LVNext Camera`, opens it at 1920×1080 as NV12 or YUY2 and shows frames. Confirm the frame rate.
3. Turn the face AI off with `set_ai_config` (needs the SDK's USB network link; if that is not set up, note it and move on).
4. With the printed mat in view, detect the four corner markers and show the flattened mat. Try the venue's worst lighting and a shadow from a hand.
5. Save 20 frames covering several layouts to `server/fixtures/` and commit them.

## hands

1. Start the Logi Hands Tracker app while our RGB capture is running. Confirm its preview stays smooth (if it drops to about 1 fps, our RGB stream is MJPG; fix that first).
2. Connect to `ws://127.0.0.1:8765` and print `index_tip`.
3. Four-touch calibration: they touch corner 0, 1, 2, 3 in turn; fit the homography; then they touch three known dots and you report the error in grid cells.
4. Pass if the error is under one cell. Otherwise try `camera_resolution` in the tracker's `config.json`, then fall back to MediaPipe on the RGB frame (`uv sync --extra mediapipe`).

## kit

1. `make kit`, print the mat and parts sheet at 100% scale on A4.
2. Measure the printed dot spacing with a ruler; it must match the script's millimetres.
3. Cut one of each part. Check each part's marker is detected at the camera height, and that a pen line between two dots is detected with the pen they will actually use.

## voice

1. In the harness, pick the LogiInsight microphone as input.
2. In a noisy part of the hall, say each prediction choice five times. Record how many were matched and how long each took.
3. Under four of five, or slower than about two seconds: make buttons the primary path and voice the extra.

## Record

Append to `docs/hardware-log.md`: date and time, device, who tested, what passed, what failed, numbers measured, decision taken. Update the row's status in `docs/tech-stack.md` from "test" to "verified" or to the fallback.
