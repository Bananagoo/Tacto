import { useCallback } from 'react'
import { useTacto } from '../useTacto'
import type { HapticsDriver } from './driver'
import { pulsePeriodMs, useBeat } from './usePulse'

// The mouse has no continuous vibration, so the buzz of a short is one preset looped fast
// enough to run together.
// TODO(haptics owner): both values are untested by feel; tune them on the real mouse.
const BUZZ_WAVEFORM = 3
const BUZZ_HZ = 25

/**
 * What the mouse does about the fingertip: separate ticks at the server's pulse rate on a
 * wire carrying current (the vibration is the current, in amps), one hard buzz on a shorted
 * path, nothing otherwise. It stops when the fingertip leaves, when the socket drops (the
 * last state is then stale) and when the page goes away.
 */
export function useProbeHaptics(driver: HapticsDriver) {
  // Single values, not the probe object: the fingertip's position changes on every state
  // message, and none of these do unless the mouse has to change what it is doing.
  const touching = useTacto((store) => store.connected && (store.state?.probe.present ?? false))
  const buzz = useTacto((store) => store.state?.probe.buzz ?? false)
  const pulseHz = useTacto((store) => store.state?.probe.pulse_hz ?? 0)

  const buzzing = touching && buzz
  const fire = useCallback(() => {
    if (buzzing) driver.playRaw(BUZZ_WAVEFORM)
    else driver.play('tick')
  }, [driver, buzzing])

  const periodMs = buzzing ? 1000 / BUZZ_HZ : touching ? pulsePeriodMs(pulseHz) : 0
  useBeat(fire, periodMs)
}
