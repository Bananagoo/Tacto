import { useCallback, useEffect, useRef } from 'react'
import type { HapticsDriver } from './driver'

// TODO(haptics owner): measure the fastest rate the mouse still renders as
// separate ticks and set this. 6 Hz is a by-feel choice, not a measurement: on 2026-11-21 the
// mock's top rate (about 8 Hz) felt a bit too quick on the real mouse with tick = 3.
export const MAX_PULSE_HZ = 6

/** Milliseconds between ticks for a pulse rate, capped at MAX_PULSE_HZ. 0 means silent. */
export function pulsePeriodMs(hz: number): number {
  if (!Number.isFinite(hz) || hz <= 0) return 0
  return 1000 / Math.min(hz, MAX_PULSE_HZ)
}

/**
 * Call `fire` now and then every `periodMs`, for as long as `periodMs` is above 0. A change
 * of period is picked up at the next beat: the timer is not torn down and restarted, which
 * would add a stray beat every time the rate moved.
 */
export function useBeat(fire: () => void, periodMs: number) {
  const periodRef = useRef(periodMs)
  useEffect(() => {
    periodRef.current = periodMs
  }, [periodMs])

  const beating = periodMs > 0
  useEffect(() => {
    if (!beating) return
    let timer: ReturnType<typeof setTimeout> | undefined
    const beat = () => {
      fire()
      // Never re-arm with a zero period: that would spin the mouse and the page.
      if (periodRef.current > 0) timer = setTimeout(beat, periodRef.current)
    }
    beat()
    return () => clearTimeout(timer)
  }, [fire, beating])
}

/** Tick the mouse at `hz` while the fingertip is on a live wire. 0 = silent. */
export function usePulse(driver: HapticsDriver, hz: number) {
  const tick = useCallback(() => driver.play('tick'), [driver])
  useBeat(tick, pulsePeriodMs(hz))
}
