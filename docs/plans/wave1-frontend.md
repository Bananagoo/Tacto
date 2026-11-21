# Wave 1: front end

**Owns:** `web/src/bench/`, `web/src/ui/`, `web/src/App.tsx`.

**Goal:** the bench view. It draws whatever circuit is in `State` on the dot grid, with the bulb glowing by `brightness`, replacing the single circle in the dev harness.

## Reuse (settle this before drawing anything)

The rule is reuse first, so do not hand-draw parts that already exist.

- **`motion`** (installed): glow and movement.
- **`@wokwi/elements`** (MIT, v1.9.2, depends on `lit`; not installed): checked on 21 Nov, it has `resistor`, `slide-switch`, `pushbutton` and `led`, and has **no battery and no incandescent bulb**. Candidate for the resistor and switch as drop-in web components.
- **Battery and bulb art**: find an openly licensed SVG source (an icon set or Wikimedia Commons electrical symbols) instead of drawing them.

First step: run the `reuse-first` skill for "SVG art for battery, bulb, resistor, switch" and report back with the proposed sources and any dependency to add. The orchestrator takes that to the user. Do not `pnpm add` anything yourself. Keep each part behind one small component so the art can be swapped.

## Tasks

1. **`bench/grid.ts`**: dot `(col, row)` → SVG coordinates; grid size as one constant, matching the mat (the vision plan's `geometry.py` owns the real numbers; mirror them and say so in a comment).
2. **`bench/Bench.tsx`**: one SVG. Draws the dot grid, wires between dots, each part between its `a` and `b` dots (rotated to fit), and the fingertip marker from `probe.x, probe.y` when `probe.present`.
3. **Parts**: `Battery`, `Bulb`, `Resistor`, `Switch` components. The bulb's glow follows `brightness` smoothly; the switch shows open or closed.
4. **Live current**: wires carrying current look different from dead ones (for example moving dashes whose speed follows `current`). A `short` circuit is visibly wrong.
5. **`App.tsx`**: show the bench in place of the single bulb circle. Keep the rest of the dev harness (readouts, tutor prompt and buttons, haptics panel) as it is.

Tutor UI, concept map and zone gauge come in a later wave.

## Checks

The web side has no test runner, and adding one is a dependency decision for the user. So: `make check` (prettier, oxlint, type-check, build) must pass, and run `make dev` in mock mode to confirm the mock circuit renders, the wheel changes the glow, and the fingertip marker moves.

## Done when

Mock state renders as a recognisable circuit and nothing in the bench hard-codes the mock's layout.

## Needs a person

Taste: the look of the parts and the glow is the user's call. Show a screenshot.
