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

## 2026-11-21, camera focus kick and gain, measured by script (Claude), arms clear of the mat (Katherine)
- Setup: camera behind the laptop as before, the v2 reference mat on the desk, nothing moving. Sharpness and corner markers sampled every half second.
- Failed: with the server sending `auto-focus=true` as it opened the camera (before frames), the picture stayed at sharpness 7 to 8 with no markers for 12 seconds on a still scene, autofocus reported on.
- Passed: sending `auto-focus=true` again while frames were flowing brought sharpness to 72 to 80 and all 4 markers in about 2 seconds (twice). Off then on one second apart did the same. Off and on in the same command did nothing.
- Passed: with the server no longer sending it at open, a freshly opened camera reached sharpness 80 and 4 markers in about 2 seconds with no kick.
- Measured, gain on the flattened v2 mat (paper brightness of 255, colour squares' saturation): gain 0: paper 181, nothing clipped, squares 0.75 to 0.99. Gain 30: paper 245, squares 0.44 to 0.89. Gain 40 and 50: paper clipped.
- Measured, squares' hue at gain 0: blue 226, cyan 204, green 148, yellow 50, red 6, magenta 340 degrees. Black reads value 31 against paper 181.
- Decision: gain stays 0. The server kicks the autofocus when no corner marker has been readable for 2 seconds, at most every 5 seconds (`vision/focus.py`).

## 2026-11-21, haptic patterns trimmed, decided by Ananya Maheshwari
- Decision: the `nudge` and `success` patterns are removed from the contract (`HapticPattern` is now `tick` and `short`). `short` = waveform 14, and the shorted-wire buzz now plays it through `play('short')` instead of a separate constant (it was waveform 3). Nothing sent `nudge` or `success`; the connect cue in `HapticsContext.tsx` now plays `tick`.
- Not yet felt: waveform 14 looped at `BUZZ_HZ` as a short.
- Decision: the shorted-wire buzz is `short` (waveform 14) looped faster: `BUZZ_HZ` raised from 25 to 40, at Ananya Maheshwari's request ("super fast"). Not felt yet; if the mouse drops presses at 40 Hz, lower it.

## 2026-11-22, piece reader on the printed mat, measured by script (Claude), layout laid by Katherine
- Setup: v2 reference mat, camera behind the laptop, gain 0, nobody's hands in view. Eight pieces on the mat.
- Passed: all 8 read right (bulb, closed switch, open switch, three wires, resistor, battery with its positive end at the red half), checked against the flattened picture by eye (Claude, from the frame). All 7 colour squares read. The reading was identical in 33 of 33 samples over 8 seconds.
- Measured: flatten 4.8 ms, read 26 ms a frame. Cover (share of the patch showing the piece's colour): 68 to 99%.
- Failed earlier the same night: re-sending `auto-focus=true` while it was already on did not refocus a parked lens (three tries, sharpness stayed 8). Off, one second, on did. The kick now does that.
- Not tested: more than one layout; hands over the mat; other lighting.

## 2026-11-22, wires read as open switches, reported by Katherine
- Passed first: with `make dev` and the live state page, the reader "worked super well" on the real mat (Katherine).
- Failed: after a while wires (blue) began to read as open switches (cyan).
- Not measured on the desk. Reproduced on rendered frames using the colours this camera sees: with the row of colour squares in shadow at 70% or 55% light, a wire read as an open switch. The squares are at the mat's edge nearest the learner, under their arms.
- Decision: each square is now measured against the paper just round it instead of the whole page's paper, so a shadow over the squares divides out, and a square with something lying beside it is not read. Whether this was the cause on the desk is not confirmed until it is tried there. `GET /debug/reader` now lists what each square reads as.

## 2026-11-22, wires against open switches on the real mat, measured by script (Claude)
- Setup: `make dev` running, 15 pieces laid by Katherine, one frame read by a second process.
- Measured: the blue and cyan squares read (22.8, 21.0, -45.4) and (37.1, 3.2, -41.5) in CIELAB, about 20 apart; most other pairs are 50 or more.
- Failed: by plain colour distance, real wires gave 9 to 42% of their pixels to "open switch". Two wires split 52% to 42% and 48% to 40%. Their pixels averaged (25, 12, -33): blue's hue, washed out.
- Passed: with hue deciding which piece colour a pixel is, the same two wires read 82% and 83% wire with 9% and 0% open switch, in a later frame where the light had changed (paper 184 against 164) and the wires were paler still. All 15 pieces kept the readings they had.
- Not tested: a real open switch beside real wires after the change (none was on the mat); only rendered values for it.
- Kit note: to this camera the cyan piece is the nearest colour to the blue one. A colour further from blue for the open switch would give more room.

## 2026-11-22, a hand over the mat changing the pieces, reported by Katherine
- Passed: the current is felt on the mouse through the live state page ("its working", Katherine). Which piece, rate and strength were not written down.
- Failed: with a hand moving over the mat, pieces came and went ("my hand is getting mistaken for components moving").
- Measured: in 12 seconds with a hand in view but still, the tracker found the hand in 174 of 202 frames and the stable reading did not change once. The failure itself was not caught on camera.
- Decision, from the three ways it can happen (all reproduced on rendered frames, none yet confirmed as the cause on the desk): the hand is now the whole shape round its joints plus the forearm running off the page, not 16 mm round each joint; what it covered stays covered for half a second after it is last seen; while a hand is about any change needs 8 agreeing frames, not 3; and a segment reads empty only where flat bare paper shows, so a sleeve holds what is under it.
- Not tested: any of this with a real hand.

## 2026-11-22, the short demo on the real mat, run by Katherine
- Setup: `VOICE_ENABLED=1 make dev`, the three-step lesson, the starting layout checked piece by piece by script (12 of 12 pieces where intended, battery + end up, circuit open at 3 V).
- Passed: the lesson run on the real mat ("its looking pretty good"); the thumb wheel turns the multimeter's dial ("the dial works now"); the current is felt again after the camera could see the mat ("ok it works").
- Measured: the setup check from the page took 3.4 s; eight checks passed and "mat found" failed with a person's arms over the corners (all four corners in 33% of frames), as it should.
- Not written down: how many full runs, and which steps were felt on the mouse.

## 2026-11-22, brightness swinging, reported by Katherine, measured by script (Claude)
- Failed: automatic brightness never stopped adjusting ("its messing up the detection"). Caught live: state adjusting, gain 34, paper 187, 2.4% of the page clipped, 43 unsure segments.
- Decision: calibrate, then hold (`vision/brightness.py`); a clipping spot is closed in on and held below.
- Passed after the change: settled at gain 6, paper 203 to 205, gain unchanged over 12 s, 12 pieces read, 0 unsure.

## 2026-11-22, the mouse connecting by itself, measured by script (Claude) on Katherine's mouse
- Passed: with no click, the lab page logged "mouse found on receiver slot 2"; the dev tools' connection test read the mouse's strength setting (30%); three play commands sent straight to the mouse were each acknowledged.
- Failed first: a second browser tab holding the mouse left the lab tab without vibration. A hidden tab now lets go, and the lab retries every 2 s.
- Not felt by Claude, who cannot feel the mouse: Katherine confirmed the vibration afterwards.

