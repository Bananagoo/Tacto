# Wave 3, vision lane: implementation plan

**Spec:** `docs/superpowers/specs/2026-11-21-tacto-platform-design.md`

**Goal:** print the paper kit from the mat's data file, and read that printed mat back through a camera into a `MatReading` plus a fingertip position, so the product runs on real paper.

**Architecture:** the mat's layout (`kit/mats/<id>.yaml`, model in `tacto/mat/models.py`) is the single source of truth. A print geometry module says where each dot lands on the page. The kit renderer draws the page from layout + geometry. The reader finds the page's four corner markers in a camera frame, flattens the image, and reads the only things a learner can change: which invited lines are drawn, and which tile sits in each slot. A source wraps the reader and the hand tracker behind `tacto.observation.Source`. Everything is tested on images the renderer makes, never on a real camera.

**Tech stack:** OpenCV (`cv2.aruco`, homography, warp), NumPy, Pillow for PDF output, MediaPipe via the existing `tacto/vision/hands.py`. No new dependencies.

## Global constraints

- Read `CLAUDE.md`, `.claude/rules/server.md` and `.claude/rules/hardware.md` first.
- Work only in your worktree. Do not push or merge. Do not add dependencies.
- Frozen (do not edit): `server/tacto/contract.py`, `server/tacto/mat/`, `server/tacto/observation.py`, `server/tacto/session.py`, `server/tacto/platform.py`, `server/tacto/app.py`, `server/tacto/world.py`, `server/tacto/main.py`, `server/tacto/vision/camera.py`, `server/tacto/vision/hands.py`, `kit/mats/`, everything under `server/tacto_bench/`, `web/`, `docs/`, `.claude/`, `CLAUDE.md`, `Makefile`, `server/pyproject.toml`, lockfiles. If one is wrong for your needs, say so in your report.
- `import cv2` only inside `server/tacto/vision/` and `kit/`.
- Product code must be clean, readable and modular: small files with one job, type hints on public functions, units in names (`_mm`, `_px`), comments that explain why. Tunable constants at the top of their file with `TODO(vision owner)`.
- Tests first. No test opens a camera, loads the MediaPipe model, or touches the network.
- Finish with `make check` passing. Small imperative commits, each ending with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.

## Files

| File | Responsibility |
|---|---|
| `server/tacto/vision/print_geometry.py` | Where the mat sits on an A4 page: dot pitch, margins, marker sizes and ids, tile sizes. Dot ↔ millimetres ↔ pixels at a given DPI |
| `server/tacto/vision/kit_render.py` | Draw the mat page and the tiles sheet as images, from a `MatLayout` |
| `kit/make_kit.py` | Command line: `--mat kit/mats/circuits-101.yaml --out kit/out` writes `mat.pdf` and `tiles.pdf` |
| `server/tacto/vision/flatten.py` | Camera frame → flattened mat image, using the four corner markers |
| `server/tacto/vision/reader.py` | Flattened image → `MatReading` (drawn lines, slot contents) |
| `server/tacto/vision/source.py` | `CameraSource` and `ReplaySource`: frames → `Observation`, with smoothing and the fingertip |
| `server/tests/vision/test_*.py` | Tests on rendered, warped and degraded images |
| `kit/README.md` | How to print and cut the kit (update) |

## Interfaces you produce

```python
# tacto/vision/print_geometry.py
CORNER_MARKER_IDS = (0, 1, 2, 3)                 # top-left, top-right, bottom-right, bottom-left
TILE_MARKER_IDS: dict[SlotContent, tuple[int, ...]]   # e.g. {"wire": (20, 21), "bulb": (10, 11), ...}
def tile_kind(marker_id: int) -> SlotContent | None: ...
@dataclass(frozen=True)
class PrintGeometry:
    @classmethod
    def for_layout(cls, layout: MatLayout) -> PrintGeometry: ...   # A4 landscape, grid centred
    def dot_mm(self, dot: Dot) -> tuple[float, float]: ...
    def corner_marker_centres_mm(self) -> list[tuple[float, float]]: ...   # in CORNER_MARKER_IDS order

# tacto/vision/kit_render.py
def render_mat(layout: MatLayout, *, dpi: int = 150) -> np.ndarray: ...     # BGR image of the page
def render_tiles(layout: MatLayout, *, dpi: int = 150) -> np.ndarray: ...
def render_tile(kind: SlotContent, marker_id: int, *, dpi: int = 150) -> np.ndarray: ...

# tacto/vision/flatten.py
@dataclass(frozen=True)
class Flattened:
    image: np.ndarray                 # the page, square-on, at FLAT_DPI
    frame_to_page: np.ndarray         # 3x3 homography, frame pixels -> page millimetres
def flatten(frame: np.ndarray, geometry: PrintGeometry) -> Flattened | None: ...   # None unless all four corners are found
def frame_point_to_mat(frame_to_page: np.ndarray, geometry: PrintGeometry, layout: MatLayout,
                       x_px: float, y_px: float) -> tuple[float, float]: ...
    # mat position: 0..1 from the first dot column/row to the last (may fall outside 0..1)

# tacto/vision/reader.py
def read_mat(flattened: Flattened, layout: MatLayout, geometry: PrintGeometry) -> MatReading: ...

# tacto/vision/source.py
class FrameSource(Protocol):                      # satisfied by a CameraWorker adapter and by tests
    def latest_frame(self) -> np.ndarray | None: ...
class FingerFinder(Protocol):                     # satisfied by an adapter over vision.hands.HandTracker
    def index_tip_px(self, frame: np.ndarray) -> tuple[float, float] | None: ...
class VisionSource:                               # satisfies tacto.observation.Source
    def __init__(self, layout: MatLayout, frames: FrameSource, fingers: FingerFinder | None = None) -> None: ...
    def observe(self) -> Observation: ...
class FolderFrames:                               # FrameSource over image files, looped (replay mode)
    def __init__(self, directory: Path) -> None: ...
```

`MatLayout`, `MatReading`, `SlotContent` are in `tacto/mat/models.py`; `Observation`, `Fingertip` in `tacto/observation.py`. Read them, and `kit/mats/circuits-101.yaml`, first.

## Behaviour

**The page.** A4 landscape. One ArUco marker (`DICT_4X4_50`, ids 0–3, 20 mm) in each corner with a quiet white border. The dot grid centred between them, dots small and grey. Printed wires as solid black lines 2 mm wide; fixed parts as their schematic symbol with their id as a small label. Each drawable as a faint dotted guide with a small "draw here" label. Each slot as a dashed outline the size of a tile, with a label of what it accepts. The mat's id and "print at 100%" with a 50 mm ruler line in the footer.

**Tiles.** Each tile is a rectangle that spans its slot (two dots apart, so its length follows the dot pitch), with the part's schematic symbol (or a straight line for a wire tile) drawn end to end and a 14 mm ArUco marker in the middle identifying its kind. Marker ids: bulbs 10–14, wires 20–24, resistors 30–34, switches 40–44. The tiles sheet holds two of each kind the layout's slots accept, with cut lines.

**Flattening.** Detect markers; require all four corner ids; fit the homography from the four marker centres to their page positions; warp to a page image at `FLAT_DPI = 100`.

**Reading drawn lines.** For each drawable, sample a strip along the segment between its two dots in the flattened image (skip the ends near the dots). Call a pixel ink when it is clearly darker than the paper around the strip. The line is drawn when ink covers at least `DRAWN_FRACTION = 0.5` of the strip's length. The printed dotted guide must not count as drawn; a hand-drawn pen line of ordinary thickness (about 0.7 mm, any dark colour) must.

**Reading slots.** Detect tile markers in the flattened image. A slot holds the kind of the tile marker whose centre is nearest the slot's midpoint, within half a dot pitch; otherwise it is empty. A tile of a kind the slot does not accept reads as empty (never raise from the reader).

**The source.** `observe()` must be cheap and never block on the camera: it returns the latest result. Each new frame is processed once.
- If the mat cannot be flattened (a corner is hidden), keep the last reading and the last homography: hands cover corners all the time.
- Smooth: a changed reading replaces the current one only after it has been seen in `STABLE_FRAMES = 3` consecutive processed frames, so a passing hand does not flicker the circuit.
- Before any frame has been read, the reading is `layout.initial_reading()`.
- The fingertip is the finder's index tip mapped through the last homography to mat position; `None` when no hand is found, when no homography exists yet, or when the point is more than half a dot outside the grid.
- `FolderFrames` returns each image file in name order, one per call, looping; an empty folder gives `None`.

## Tasks

Each task: write the tests, watch them fail, implement, watch them pass, commit.

1. **Print geometry.** Tests: every dot of the Circuits 101 layout lies inside the page and inside the rectangle of corner markers with at least 10 mm to spare; dot pitch is the same in both directions; marker ids map to kinds and unknown ids map to `None`.
2. **Kit renderer and `make_kit.py`.** Tests: the rendered mat contains exactly the four corner markers, detectable with `cv2.aruco`; rendered tiles carry a marker of the right kind; `make kit` (already in the Makefile; check its arguments match your script, and report if the Makefile needs a change) writes both PDFs at A4 size.
3. **Flatten.** Build a test helper that takes the rendered page and warps it with a known perspective onto a larger grey background, with optional blur, brightness change and noise. Tests: flatten recovers the page so that known dots land within 1.5 mm; three visible corners gives `None`; `frame_point_to_mat` maps the frame position of a known dot to its mat position within 0.02.
4. **Reader.** A test helper that composes a scene: the rendered mat, plus pen lines drawn on named drawables, plus tiles pasted on named slots, then warped. Tests: the untouched kit reads as the initial reading (after pasting the starting tiles); each drawable alone and both together; each slot with each kind it accepts and empty; a tile of the wrong kind reads as empty; the dotted guide is not a drawn line; a pen line drawn 60% of the way counts and 30% does not; all of it again under blur, a 30% brightness drop and a strong perspective.
5. **Source.** Tests with a fake frame list and a fake finger finder: starts as the initial reading; a change appears only after three consecutive frames; a single odd frame is ignored; frames with a hidden corner keep the last reading; the fingertip maps to the right mat position and is `None` off the mat or with no hand; `observe()` called many times between frames processes each frame once; `FolderFrames` loops and handles an empty folder.

## Review focus

- A frame that is blank, tiny, greyscale or has an alpha channel must not raise.
- Two tiles near one slot, or the same marker id seen twice, must not raise and must pick the nearest.
- A hand covering a slot must not turn its tile into "empty" within three frames' worth of flicker; state plainly in your report what a long occlusion does.
- A mat rotated 180 degrees in front of the camera must still read correctly (the corner ids fix the orientation).
- `observe()` must stay under a millisecond when no new frame has arrived.

## Needs a person

Print `kit/out/mat.pdf` and `kit/out/tiles.pdf` at 100%, check the 50 mm ruler, cut the tiles, mount the camera above the mat so the paper fills most of the picture (the camera's auto-exposure washes out white paper against a dark background), and record frames into `server/fixtures/`.
