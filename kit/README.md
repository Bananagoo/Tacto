# The mat

The printable mat: a grid of dots between four corner markers. The card pieces are cut by hand from coloured card and carry no markers, so the mat is the only thing printed.

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

The grid must fit between the corner markers: `(cols - 1) * dot_pitch_mm` at most 231 mm and `(rows - 1) * dot_pitch_mm` at most 144 mm. `make kit` says so if it does not. These values are placeholders until the kit owner decides them.

## Print

1. Print at **100%** ("actual size"; not "fit to page") on plain white A4.
2. Hold a ruler against the bar in the footer: it must measure 50 mm. If it does not, the print was scaled; print again.
3. Keep the four corner squares clean and flat, with their white edge. The camera needs all four to find the mat.

## Pieces

Each piece is a strip of card as long as one dot gap, one colour per type. Proposed colours, not final: wire black, battery red, bulb yellow, resistor blue, switch green. Avoid skin tones and white. If the battery card has a marked positive end, tell the vision owner how it is marked.

## Camera

Mount the camera straight above the mat so the paper fills most of the picture and all four corners are visible. White paper against a dark desk washes out under the camera's auto-exposure when the paper is small in the frame.
