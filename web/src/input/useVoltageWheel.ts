import { useEffect } from 'react'
import { useTacto } from '../useTacto'
import { tallyWheel } from './wheel'

/**
 * The scroll wheel is the voltage dial: it sends `wheel` steps and the server owns the
 * volts. Sign: deltaY is added as it comes, which makes scrolling up raise the voltage on
 * the demo laptop (macOS natural scrolling on; confirmed 2026-11-21, docs/hardware-log.md).
 */
export function useVoltageWheel() {
  useEffect(() => {
    let remainder = 0
    const onWheel = (event: WheelEvent) => {
      const tally = tallyWheel(remainder, event.deltaY)
      remainder = tally.remainder
      // `send` is read at the moment of use: it is replaced on every reconnect.
      if (tally.steps !== 0) useTacto.getState().send({ type: 'wheel', steps: tally.steps })
    }
    // Passive: this never blocks scrolling, so the browser need not wait for it.
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => window.removeEventListener('wheel', onWheel)
  }, [])
}
