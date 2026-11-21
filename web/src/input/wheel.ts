// TODO(front end owner): 40 suits the MX Master 4's smooth scrolling on the demo laptop;
// recheck if the wheel feels too coarse or too twitchy there.
/** Scroll distance, in the browser's wheel units, that makes one voltage step. */
export const WHEEL_UNITS_PER_STEP = 40

export interface WheelTally {
  /** Whole steps to send now; positive means more volts. */
  steps: number
  /** Scroll distance left over, carried into the next event. */
  remainder: number
}

/**
 * Add one wheel event to the running total and take out the whole steps. Smooth-scroll mice
 * send many small deltas, so the leftover has to be kept between events or slow scrolling
 * would never add up to a step.
 */
export function tallyWheel(remainder: number, deltaY: number): WheelTally {
  const total = remainder + deltaY
  const steps = Math.trunc(total / WHEEL_UNITS_PER_STEP)
  return { steps, remainder: total - steps * WHEEL_UNITS_PER_STEP }
}
