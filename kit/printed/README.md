# What was printed

The two sheets on the desk on 21 Nov 2026. Both are A4 landscape, printed at 100%, with a 50 mm check bar. The numbers below were read out of the PDFs' drawing commands, not measured on paper.

## `mat.pdf`

The same geometry as `make kit` (`kit/mats/circuits-101.yaml`, `server/tacto/vision/print_geometry.py`):

- 9 × 6 dots, 28 mm apart. First dot centre 36.5 mm from the left edge, 35 mm from the top.
- Dots are grey (150, 150, 150), 1.8 mm across.
- Four black corner markers, 20 mm square, 8 mm in from each edge.

## `mat-with-reference.pdf`

Added 21 Nov. The same mat (dots, markers and bar in the same places) with six 12 mm colour squares along the top edge, 8 mm from the top, between the two upper markers. The camera can read them in every frame to learn what each colour looks like under the light of the moment.

| Square, left edge at | Colour (R, G, B) | Piece sheet has |
|---|---|---|
| 72.5 mm | blue (32, 64, 192) | (30, 70, 210) |
| 100.5 mm | green (24, 160, 72) | (20, 165, 50) |
| 128.5 mm | yellow (255, 230, 0) | (255, 225, 0) |
| 156.5 mm | magenta (216, 27, 154) | (215, 0, 170) |
| 184.5 mm | red (224, 32, 32) | (220, 20, 20) |
| 212.5 mm | black (0, 0, 0) | (0, 0, 0) |

Two gaps: there is no cyan square for the open switch, and the squares are close to the pieces' colours but not the same values.

Both are fixed in `mat-with-reference-v2.pdf`. Print that one, not this one.

## `mat-with-reference-v2.pdf`

Added 21 Nov. `mat.pdf` with seven 12 mm colour squares along the top edge, 8 mm from the top, 28 mm apart. Each square is centred above one of dot columns 2 to 8 and is 30.5 mm clear of the nearest corner marker. The fills are the piece sheet's own drawing commands, copied from `components-v3.pdf`, so a square and its piece print with the same ink. The order follows the piece sheet's rows.

| Square, left edge at | Stands for | Colour (R, G, B) |
|---|---|---|
| 58.5 mm | wire | blue (30, 70, 210) |
| 86.5 mm | bulb | yellow (255, 225, 0) |
| 114.5 mm | resistor | magenta (215, 0, 170) |
| 142.5 mm | switch, closed | green (20, 165, 50) |
| 170.5 mm | switch, open | cyan (0, 175, 180) |
| 198.5 mm | battery, positive half | red (220, 20, 20) |
| 226.5 mm | battery, negative half | black (0, 0, 0) |

Checked on a 150 dpi render: nothing outside the band of squares differs from `mat.pdf`, each square's centre is its piece's exact value, and OpenCV still finds corner markers 0 to 3. Not checked: the printed sheet under the camera. The squares only stand for the pieces if both sheets come off the same printer on the same paper.

The reader samples these squares in every frame (`server/tacto/vision/classify.py`), and `make kit` draws them from `kit/pieces.yaml`.

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

- `kit/pieces.yaml` holds these colours.
- The battery's positive end can now be seen: it is the red half.
- There are two switch pieces, open and closed, so the camera could read a switch's state from the piece.
- The closest pair of colours is blue and cyan, 45° of hue apart; green and cyan are 50° apart.
