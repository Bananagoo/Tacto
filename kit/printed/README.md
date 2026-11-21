# What was printed

The two sheets on the desk on 21 Nov 2026. Both are A4 landscape, printed at 100%, with a 50 mm check bar. The numbers below were read out of the PDFs' drawing commands, not measured on paper.

## `mat.pdf`

The same geometry as `make kit` (`kit/mats/circuits-101.yaml`, `server/tacto/vision/print_geometry.py`):

- 9 × 6 dots, 28 mm apart. First dot centre 36.5 mm from the left edge, 35 mm from the top.
- Dots are grey (150, 150, 150), 1.8 mm across.
- Four black corner markers, 20 mm square, 8 mm in from each edge.

## `components-v3.pdf`

Printed pieces with a symbol on each, not plain card. Every piece is 25 mm long, so it leaves 1.5 mm free at each dot, and 9 mm wide at its ends; most have a wider middle.

| Piece | Colour (R, G, B) | Hue | Shape | On the sheet |
|---|---|---|---|---|
| Wire | blue (30, 70, 210) | 227° | plain 25 × 9 mm | 36 |
| Bulb | yellow (255, 225, 0) | 53° | 14 mm disc in the middle, black ⊗ | 9 |
| Resistor | magenta (215, 0, 170) | 313° | 15 × 13 mm middle, white zigzag | 9 |
| Switch, closed | green (20, 165, 50) | 132° | 16 × 13 mm middle, black bar between two dots | 9 |
| Switch, open | cyan (0, 175, 180) | 182° | 16 × 13 mm middle, black lifted bar | 9 |
| Battery | red (220, 20, 20) half and black half | 0° | 17 × 13 mm middle; `+` on the red half, `−` on the black half | 9 |

## What this changes for the camera reader

- `kit/pieces.yaml` still holds the first proposal (black wire, blue resistor, one switch colour, an all-red battery). It does not match this sheet.
- The battery's positive end can now be seen: it is the red half.
- There are two switch pieces, open and closed, so the camera could read a switch's state from the piece.
- The closest pair of colours is blue and cyan, 45° of hue apart; green and cyan are 50° apart.
