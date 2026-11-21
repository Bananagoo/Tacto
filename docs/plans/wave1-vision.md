# Wave 1: vision and paper kit

**Owns:** `server/tacto/vision/`, `kit/`, `server/fixtures/`, `server/tests/test_vision_*.py`, `server/tests/test_kit_*.py`.

**Goal:** a printable kit, and code that reads a photo of that kit back into mat geometry and parts. No camera in this wave: the test images are rendered from the kit itself.

## Reuse

- **`cv2.aruco`** (installed, `DICT_4X4_50`): marker generation and detection. Check which API the installed OpenCV exposes (`ArucoDetector` class vs the older functions) before writing code.
- **OpenCV**: `findHomography`, `warpPerspective`.
- **Pillow** (installed): composing the A4 pages and saving PDF.

No new dependencies expected. Nothing here should be written by hand that OpenCV already does.

## Tasks

1. **`vision/geometry.py`**: the single source of truth for the kit, imported by both the kit script and the reader: A4 size, dot spacing in mm, columns and rows, corner marker ids and positions, marker size, and the table of marker id → part kind (several ids per kind so two bulbs can be on the mat). Helpers: dot ↔ mm ↔ flattened-image pixel.
2. **`kit/make_kit.py`**: `--out DIR` renders `mat.pdf` (dot grid, one ArUco marker in each corner, a "print at 100%" ruler line) and `parts.pdf` (battery, bulb, resistor, switch cut-outs; each spans two dots, carries its marker and has a clear label and polarity mark on the battery). `make kit` already calls it.
3. **`vision/mat.py`**: image → four corner markers → homography → flattened mat image. Returns "mat not found" cleanly when fewer than four corners are visible.
4. **`vision/parts.py`**: in the flattened image, detect part markers and return contract `Part`s: kind from the id, dots `a` and `b` from the marker's position and rotation, snapped to the grid.

Wire reading (ink per dot-to-dot segment) is Wave 2: it needs the flattened image from task 3 first, and real pen on real paper to tune.

## Tests (write first)

- Geometry round trip: dot → pixel → dot for every dot.
- Render the mat to an image, paste part markers at known dots and rotations, warp the whole thing with a known perspective and some blur, then read it back: the corners are found, and every part comes back with the right kind and dots.
- Three corners visible: mat not found, no exception.
- The kit script writes both PDFs at A4 size.

## Done when

`make check` passes and `make kit` writes `kit/out/mat.pdf` and `kit/out/parts.pdf`.

## Needs a person

Print both at 100%, measure the dot spacing with a ruler, cut the parts. Then, with the camera, save 20 frames to `server/fixtures/`.
