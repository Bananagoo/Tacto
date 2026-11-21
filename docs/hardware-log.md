# Hardware log

One entry per test on real hardware. `/hardware-check` appends here. Claude cannot see the desk or feel the mouse, so this file is the only evidence that something works.

Format:

```
## 2026-11-21 15:10, mouse, tested by <name>
- Passed:
- Failed:
- Measured:
- Decision:
```

## 2026-11-21, mouse, tested by Ananya 
- Passed: `webhid` driver connects in Chrome and fires pulses from `web/haptics-test.html`.
- Failed: `haptic-web` driver does not connect. Nothing listens on 127.0.0.1:41443 because Logi Options+ and the Haptic Web plugin are not installed on this laptop.
- Measured: nothing yet. Waveform feel (0 to 14) and the fastest separate-tick rate are still to do.
- Decision: use `webhid` for now; the plugin stays optional.

## 2026-11-21, mouse wheel, tested by Ananya Maheshwari
- Passed: pulse rate rises with the voltage in the dev harness (mock mode, `webhid`).
- Failed: scrolling up lowered the voltage (direction reversed on this laptop).
- Decision: flipped the sign in `web/src/App.tsx` (`-=` to `+=` on `event.deltaY`). This assumes macOS natural scrolling is on. Recheck the direction on the demo laptop; if it is reversed there, either turn natural scrolling off for the mouse or flip the sign back.

## 2026-11-21, mouse waveform for `tick`, tested by Ananya Maheshwari
- Decision: `tick` = waveform 0, chosen by feel on `webhid`. `nudge` (2), `short` (13) and `success` (7) are still placeholders.
- Not measured yet: `MAX_PULSE_HZ` (still the placeholder 12), and whether the plugin's index 0 feels the same as webhid's.

## 2026-11-21, mouse waveform for `tick` (revised), tested by Ananya Maheshwari
- Decision: `tick` = 3, confirmed by feel on `webhid` after trying 0 and 6. The plugin calls index 3 `damp_collision`; webhid ids are not confirmed against those names.
- Still open: `MAX_PULSE_HZ` (placeholder 12), and `nudge` (2), `short` (13), `success` (7) placeholders.

## 2026-11-21, mouse tick rate, tested by Ananya Maheshwari
- Failed: the mock's top rate (about 8 Hz at full voltage) felt a bit too quick with `tick` = 3.
- Decision: `MAX_PULSE_HZ` lowered from 12 to 6 in `web/src/haptics/usePulse.ts`. This is a feel choice, not a measured limit of the mouse. Above about 6 V the mock's rate is held at 6 Hz, so higher voltage stops changing the tick rate.

## 2026-11-21, mouse through the Logi Bolt receiver, tested by Katherine
- Passed: `webhid` driver connects when "USB Receiver" is picked in Chrome and fires waveforms (felt by hand). The driver finds the mouse on receiver slot 2 by pinging slots 1 to 6.
- Passed: the plugin route is still not installed on this laptop (no Logi Options+), so `webhid` over the receiver is the working route here.
- Measured (read from the mouse over HID++, not felt): the haptic feature is 0x19b0 at index 0x0b; it reports exactly 15 presets, 0 to 14; haptics enabled, strength 60 of 100, full 0 to 100 range supported. Writing strength 60 back was accepted.
- Not tested by feel yet: whether changing strength is noticeable, and which preset and rate loop into a steady buzz.
- Decision: `MAX_WAVEFORM_INDEX` = 14. Strength is exposed as `setStrength` on the driver and as a slider on the haptics test page.

## 2026-11-21, mouse strength and speed, tested by Katherine
- Passed: on the haptics test page with `webhid` over the receiver, the speed slider changes the tick rate and the strength slider changes how strong the vibration feels. Both confirmed by hand.
- Not measured yet: the preferred preset, the fastest rate that still feels like separate ticks, and the strength to use in the demo.

## 2026-11-21, camera exposure, measured by script (Claude), picture checked by Katherine in the bench
- Setup: camera on its stand facing the learner across the desk, mat on a grey table, dark floor behind, hall lighting. Camera held open, 1080p.
- Failed: on auto-exposure the paper clipped (brightest 1% of pixels at 232 to 254 of 255) and 0 to 2 of the 4 corner markers were read.
- Failed: OpenCV cannot change it on macOS. `capture.set` was refused for exposure, auto-exposure, brightness, gain and contrast.
- Passed: `uvc-util` sees the camera (`LVNext`, 046d:094f) and sets `auto-exposure-mode=1` (manual). At gain 0, exposure time 156: brightest 1% at 187, nothing clipped, all 4 markers in 3 of 5 readings and 3 of 4 in the other two (hands were moving and autofocus was hunting).
- Measured: gain 60 clipped 17% of the frame; gain 150 clipped 46%. Exposure time 20 gave a near-black picture; 60, 156 and 400 gave the same brightness.
- Not tested: whether the setting survives unplugging the camera; the same numbers with the camera mounted above the mat.
- Decision: the server sets manual exposure, gain 0, every time it opens the camera. The bench has a gain slider.

## 2026-11-21, camera focus, measured by script (Claude)
- Setup: as the exposure entry above, components scattered on the mat. Sharpness is the variance of the Laplacian of the 1080p frame.
- Failed: focus cannot be locked. With autofocus on, the mat settled at sharpness 70 to 95 and 3 or 4 corner markers were read. Each time autofocus was turned off (`auto-focus=false`, three times) sharpness fell to about 7 within a second and no marker was read; turning it back on recovered in about 2 seconds. The camera offers no focus distance control.
- Failed: with autofocus on, hands on the laptop in front of the camera pull the focus off the mat (sharpness 3 to 8, no markers) for as long as they stay there.
- Decision: autofocus stays on; the server switches it on whenever it opens the camera. Keep near objects (the laptop, hands on its trackpad) out of the camera's view. Readings must hold through soft frames.
