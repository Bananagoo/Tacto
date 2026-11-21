import { useEffect } from 'react'
import type { HapticsDriver } from './driver'

// TODO(haptics owner): measure the fastest rate the mouse still renders as
// separate ticks and set this. 12 Hz is a placeholder, not a measurement.
export const MAX_PULSE_HZ = 12

/** Tick the mouse at `hz` while the fingertip is on a live wire. 0 = silent. */
export function usePulse(driver: HapticsDriver, hz: number) {
  useEffect(() => {
    if (hz <= 0) return
    const period = 1000 / Math.min(hz, MAX_PULSE_HZ)
    driver.play('tick')
    const timer = setInterval(() => driver.play('tick'), period)
    return () => clearInterval(timer)
  }, [driver, hz])
}
