# The mat

The printable mat: a grid of dots between four corner markers, with seven reference colour squares along its top edge. The pieces are printed in flat colours and carry no markers.

**The mat must be printed from this script**, not drawn separately: the camera reader measures against the same geometry the script prints from.

## Make it

```
make kit
```

writes `kit/out/mat.pdf` (A4 landscape, 300 dpi) from `kit/mats/circuits-101.yaml`.

## Change the grid

Edit `kit/mats/circuits-101.yaml`:

```yaml
id: circuits-101
cols: 9            # dots across
rows: 6            # dots down
dot_pitch_mm: 28   # centre to centre; a piece spans one gap, so this is the piece length
```

The grid must fit between the corner markers: `(cols - 1) * dot_pitch_mm` at most 231 mm and `(rows - 1) * dot_pitch_mm` at most 144 mm. `make kit` says so if it does not.

## Print

1. Print at **100%** ("actual size"; not "fit to page") on plain white A4.
2. Hold a ruler against the bar in the footer: it must measure 50 mm. If it does not, the print was scaled; print again.
3. Keep the four corner squares clean and flat, with their white edge. The camera needs all four to find the mat.

## Pieces

The pieces are printed and cut out: `kit/printed/components-v3.pdf`. Each is as long as one dot gap and one flat colour, which is how the camera tells them apart (`kit/pieces.yaml`):

| Piece | Colour |
|---|---|
| Wire | blue |
| Bulb | yellow |
| Resistor (22 Ω) | magenta |
| Switch, closed | green |
| Switch, open | cyan |
| Battery | red at its positive end, black at the other |

The mat carries a square of each colour along its top edge. The camera reads those squares in every frame, so the pieces are matched to the colours as they look under the room's light. Keep the squares uncovered, and tape pieces down from underneath or with matte tape: shiny tape glares.

## Camera

The camera can sit behind the laptop and look across the desk at an angle: the four corner markers flatten the page. All four corners must be in view. Before a demo, run the setup check (`README.md`).
