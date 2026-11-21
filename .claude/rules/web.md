---
paths:
  - "web/**"
---

# Web rules

- `pnpm` only. `pnpm build` runs the type-check; `pnpm lint` runs oxlint.
- All server data comes from the `useTacto` store. Components do not open sockets or call `fetch` on the server themselves.
- The page must render something sensible when `state` is `null` and when the server is disconnected.
- `web/src/` belongs to the UI team; the vision lane does not edit it. The contract it reads is `contract/state.schema.json`.
- The bench view is SVG driven directly by `State`: no local copy of circuit data, no physics in the browser. If the screen needs a number, the server sends it.
- Animate with `motion` or CSS. Keep anything that runs per state message (15 per second) cheap: no layout thrash, no new objects in render that break memoisation of large subtrees.
- The projected screen is what judges see from two metres away: large type, high contrast, one focal point at a time. The lesson prompt is always visible as text.
- No chat UI, no text input for the learner.
- Tooling pages (camera bench, haptics page) live in `web/devtools/`, served at `/devtools/` by `make bench`. The hand-set mat is served by the Python server at `localhost:8000/manual`. Nothing under `web/src/` may import from `web/devtools/`.
