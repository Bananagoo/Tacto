import { useCallback } from 'react'
import type { HapticPattern } from './contract'
import { useHaptics } from './haptics/useHaptics'
import { useProbeHaptics } from './haptics/useProbeHaptics'
import { useVoltageWheel } from './input/useVoltageWheel'
import { useTactoConnection } from './useTacto'

/**
 * The live links between the page, the server and the mouse: the socket, the wheel as the
 * voltage dial and the vibration under the fingertip. It draws nothing, and it is its own
 * component so that none of this can cause the layout to render again.
 */
export function Instrument() {
  const { driver } = useHaptics()
  const playPattern = useCallback((pattern: HapticPattern) => driver.play(pattern), [driver])

  useTactoConnection(playPattern)
  useVoltageWheel()
  useProbeHaptics(driver)
  return null
}
