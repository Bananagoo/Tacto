// How the state's vibration strength (0 to 1, proportional to the current under the
// fingertip) becomes the mouse's strength setting (0 to 100).

// TODO(haptics owner): tune both by feel on the real mouse.
// The faintest current still has to be felt, so 0..1 is spread over this floor up to 100.
export const MIN_STRENGTH_PERCENT = 25
// Strength is a setting stored on the mouse, written over HID: only send a change this big.
export const STRENGTH_STEP_PERCENT = 5

export function strengthPercent(strength: number): number {
  const clamped = Math.min(1, Math.max(0, strength))
  const percent = MIN_STRENGTH_PERCENT + clamped * (100 - MIN_STRENGTH_PERCENT)
  return Math.round(percent / STRENGTH_STEP_PERCENT) * STRENGTH_STEP_PERCENT
}
