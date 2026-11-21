---
name: hardware-check
description: Walk a teammate through one hardware de-risk test and record the result. Use when the user runs /hardware-check, or says they have the mouse or camera in hand and want to test it.
argument-hint: "[mouse | camera | hands | kit]"
disable-model-invocation: true
---

Run the hardware check for **$ARGUMENTS** with the person who has the device. You cannot see the desk or feel the mouse: you give one step at a time, they tell you what happened, and you write it down.

Read `.claude/rules/hardware.md` first. Then follow the matching section. Ask for the result of each step before giving the next. If a step fails twice, stop and write down what was tried instead of looping.

## mouse

The UI team owns the haptics code; this check only records what a person feels.

1. `make bench`, open http://localhost:5173/devtools/#haptics in Chrome, click Connect and pick the mouse (through the Logi Bolt receiver).
2. Loop the tick preset at 1.5, 3 and 6 a second. Can they tell the three apart? Those are series, one bulb and the parallel battery wire.
3. Loop the buzz preset fast. Is it clearly a warning and not a faster tick?
4. Note the preset numbers, speed and strength they prefer.

## camera

1. Camera mounted looking straight down at the mat, paper filling most of the frame, on a USB 3 port.
2. `make bench`, open http://localhost:5173/devtools/#camera, pick `LVNext Camera`, start it. Confirm the frame rate.
3. Tick Markers with the printed mat in view. Are all four corners found? Try the venue's worst lighting and a shadow from a hand.
4. Record frames of several layouts with `scripts/record_frames.py` into `server/fixtures/` (no faces in view).
5. Stop the camera when done; it must not stream between steps.

## hands

1. In the camera bench, tick Hand points. Are the 21 points on the hand, and does the index tip follow?
2. With the mat in view, they touch three known dots; report how far the fingertip reading is from each, in dot spacings.
3. Pass if every one is within a third of a dot spacing (the reach used for "touching a piece").

## kit

1. `make kit`, print `kit/out/mat.pdf` at 100% scale on A4.
2. Measure the 50 mm bar and the dot spacing with a ruler; they must match the mat file.
3. Lay one card piece of each colour on the mat under venue lighting and save a frame of each for the classifier.

## Record

Append to `docs/hardware-log.md`: date and time, device, who tested, what passed, what failed, numbers measured, decision taken. Update the row's status in `docs/tech-stack.md` from "test" to "verified" or to the fallback.
