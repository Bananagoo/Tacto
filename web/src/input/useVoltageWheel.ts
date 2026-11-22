import { useEffect } from 'react'
import { MAX_VOLTS } from '../contract'
import { useTacto } from '../useTacto'
import { tallyWheel } from './wheel'

// TODO(front end owner): tune on the real wheel. Volts for one wheel step.
const VOLTS_PER_STEP = 0.5

/**
 * The scroll wheel is the voltage dial: each step asks the server for half a volt more or
 * less (`set_voltage`), between 0 and MAX_VOLTS. Sign: deltaY is added as it comes, which makes scrolling up raise the voltage on
 * the demo laptop (macOS natural scrolling on; confirmed 2026-11-21, docs/hardware-log.md).
 */
export function useVoltageWheel() {
  const connected = useTacto((store) => store.connected)
  const voltageInputEpoch = useTacto((store) => store.voltageInputEpoch)
  useEffect(() => {
    if (!connected) return
    let remainder = 0
    // What was last asked for, so a fast spin adds up without waiting for each answer.
    let asked: number | null = null
    // Once acknowledged, use the server's value again, including a reset from another tab.
    const unsubscribe = useTacto.subscribe(({ state }) => {
      if (state?.circuit.source_voltage === asked) asked = null
    })
    const onWheel = (event: WheelEvent) => {
      const tally = tallyWheel(remainder, event.deltaY)
      remainder = tally.remainder
      if (tally.steps === 0) return
      // `send` and the state are read at the moment of use: both change under the handler.
      const { send, state } = useTacto.getState()
      const from = asked ?? state?.circuit.source_voltage
      if (from === undefined) return
      asked = Math.min(MAX_VOLTS, Math.max(0, from + tally.steps * VOLTS_PER_STEP))
      send({ type: 'set_voltage', volts: asked })
    }
    // Passive: this never blocks scrolling, so the browser need not wait for it.
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => {
      unsubscribe()
      window.removeEventListener('wheel', onWheel)
    }
  }, [connected, voltageInputEpoch])
}
