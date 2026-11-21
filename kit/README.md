# Paper kit

The printable mat and its tiles. Owned by the vision lane.

## Make it

```
make kit
```

writes `kit/out/mat.pdf` and `kit/out/tiles.pdf` (A4 landscape, 300 dpi) from `kit/mats/circuits-101.yaml`. For another mat, from `server/`:

```
uv run python ../kit/make_kit.py --mat ../kit/mats/<id>.yaml --out ../kit/out
```

## Print and cut

1. Print both pages at **100%** ("actual size"; not "fit to page") on plain white A4, in black and white or colour.
2. Hold a ruler against the bar in each footer: it must measure 50 mm. If it does not, the print was scaled; print again.
3. Cut each tile along its grey outline. Keep the white edge around the square pattern: the camera cannot find a pattern cut to its black border.
4. Lay the tile named on the mat ("starts with the wire") in its dashed slot. Any way round is fine.

Flat paper matters: stick the mat to the desk or a board with tape at the edges, outside the four corner squares. Thin card for the tiles makes them easier to pick up.

## Use it

- **Corner squares** (markers 0 to 3) tell the camera where the page is and which way up. All four must be visible for the mat to be read; while a hand hides one, the last reading is kept.
- **Dotted lines marked "draw here"** are where the learner draws with an ordinary dark pen (ballpoint, fineliner, soft pencil). A line covering at least half the gap counts. A highlighter or a hard pencil is too faint.
- **Dashed boxes** are slots. A tile is in a slot when its pattern is within 14 mm of the slot's middle. A hand resting on a tile's pattern for longer than a moment reads as the tile being taken away; point at the wires, not at the pattern.
- Mount the camera so the paper fills most of the picture. White paper on a dark desk makes the camera over-expose and wash the page out.

## Where the numbers live

`server/tacto/vision/print_geometry.py` holds every size and marker id; the renderer (`kit_render.py`) and the reader (`flatten.py`, `reader.py`) both import it, so the paper and the software cannot disagree.

| Thing | Value |
|---|---|
| Dot pitch | 28 mm, the same for every mat, so tiles are interchangeable |
| Corner markers | `DICT_4X4_50` ids 0, 1, 2, 3 (top-left, then clockwise), 20 mm |
| Tile | 56 x 24 mm (two dots long), 14 mm marker in the middle |
| Tile marker ids | bulb 10-14, wire 20-24, resistor 30-34, switch 40-44 |

## Recording frames for replay

Save camera frames as `.png` or `.jpg` in a folder under `server/fixtures/`. `tacto.vision.source.FolderFrames` plays a folder back in file-name order, looping, so number the files (`0001.png`, ...). Nothing in the frames should show a person's face.
