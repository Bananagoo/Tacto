---
paths:
  - "web/**"
---

# Web rules

- `pnpm` only. `pnpm build` runs the type-check; `pnpm lint` runs oxlint.
- All server data comes from the `useTacto` store. Components do not open sockets or call `fetch` on the server themselves, except `voice/` posting audio.
- The page must render something sensible when `state` is `null` and when the server is disconnected.
- The bench view is SVG driven directly by `State`: no local copy of circuit data, no physics in the browser. If the screen needs a number, the server sends it.
- Animate with `motion` or CSS. Keep anything that runs per state message (15 per second) cheap: no layout thrash, no new objects in render that break memoisation of large subtrees.
- The projected screen is what judges see from two metres away: large type, high contrast, one focal point at a time. The tutor's prompt is always visible as text as well as spoken.
- Prediction buttons are always on screen during the predict phase, even when voice works.
- No chat UI, no text input for the learner.
- `App.tsx` is currently a dev harness. Keep a route or query flag (`?dev`) that still shows it once the real UI exists; it is how haptics get tested.
