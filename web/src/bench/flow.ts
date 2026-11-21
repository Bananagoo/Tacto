// How the moving dashes on a live wire follow the current. This is a drawing choice, not
// physics: the amps come from the server and are only turned into a speed on screen here.

// TODO(front end owner): tune these on the projector with the real lesson's currents.
/** Below this a wire is drawn as dead; the solver can leave tiny leftover currents. */
const MIN_VISIBLE_AMPS = 0.001
const SPEED_PER_AMP = 300
/** Slow enough to read as "barely flowing", fast enough to be seen moving from two metres. */
const MIN_SPEED = 40
/** A short circuit's current is huge; past this speed the dashes blur into a solid line. */
const MAX_SPEED = 500

/** Length of one dash plus one gap, in SVG units. */
export const DASH_PERIOD = 40
export const DASH_ARRAY = '14 26'

/**
 * Dash speed in SVG units per second, signed like the current (positive runs a -> b).
 * 0 means the wire is dead.
 */
export function flowSpeed(amps: number): number {
  if (!Number.isFinite(amps) || Math.abs(amps) < MIN_VISIBLE_AMPS) return 0
  const speed = Math.min(MAX_SPEED, Math.max(MIN_SPEED, Math.abs(amps) * SPEED_PER_AMP))
  return Math.sign(amps) * speed
}
