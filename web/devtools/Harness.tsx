// Dev harness, not the product UI. It proves the loop end to end against the mock world:
// scroll wheel -> server -> state -> bulb glow + mouse pulse. Needs `make bench`.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { HapticPattern } from '../src/contract'
import { DRIVERS, MAX_WAVEFORM_INDEX, type DriverName } from '../src/haptics/driver'
import { usePulse } from '../src/haptics/usePulse'
import { useTacto, useTactoConnection } from '../src/useTacto'

const WHEEL_UNITS_PER_STEP = 40

export default function Harness() {
  const [driverName, setDriverName] = useState<DriverName>('console')
  const [driverError, setDriverError] = useState('')
  const driver = useMemo(() => DRIVERS[driverName](), [driverName])
  const onHaptic = useCallback((pattern: HapticPattern) => driver.play(pattern), [driver])

  useTactoConnection(onHaptic)
  const { connected, state, send } = useTacto()
  usePulse(driver, state?.probe.present ? state.probe.pulse_hz : 0)

  // Scroll wheel = voltage dial. Smooth-scroll mice send many small deltas.
  // Sign: `+=` so that, with macOS natural scrolling on (the default), scrolling up raises the
  // voltage. Flipped from `-=` on 2026-11-21 after testing on the real mouse; if the demo laptop
  // has natural scrolling off, the direction will be reversed there (see docs/hardware-log.md).
  const wheelRemainder = useRef(0)
  useEffect(() => {
    const onWheel = (event: WheelEvent) => {
      wheelRemainder.current += event.deltaY
      const steps = Math.trunc(wheelRemainder.current / WHEEL_UNITS_PER_STEP)
      if (steps !== 0) {
        wheelRemainder.current -= steps * WHEEL_UNITS_PER_STEP
        send({ type: 'wheel', steps })
      }
    }
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => window.removeEventListener('wheel', onWheel)
  }, [send])

  // Flash a dot whenever any driver fires, so people watching can see the pulse.
  const [flash, setFlash] = useState(false)
  useEffect(() => {
    const onFire = () => {
      setFlash(true)
      setTimeout(() => setFlash(false), 60)
    }
    window.addEventListener('tacto:haptic', onFire)
    return () => window.removeEventListener('tacto:haptic', onFire)
  }, [])

  const connectDriver = async () => {
    setDriverError('')
    try {
      await driver.connect()
      driver.play('success')
    } catch (error) {
      setDriverError(error instanceof Error ? error.message : String(error))
    }
  }

  const bulb = state?.circuit.parts.find((part) => part.kind === 'bulb')
  const glow = bulb?.brightness ?? 0

  return (
    <main className="mx-auto flex h-full max-w-3xl flex-col gap-6 p-8">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Tacto dev harness</h1>
        <span className={connected ? 'text-emerald-400' : 'text-rose-400'}>
          {connected ? `server: ${state?.source ?? '…'}` : 'server: disconnected'}
        </span>
      </header>

      <section className="flex items-center gap-8 rounded-xl bg-white/5 p-6">
        <svg viewBox="0 0 120 120" className="h-40 w-40">
          <circle cx="60" cy="60" r={28 + 26 * glow} fill="#ffd166" opacity={0.25 * glow} />
          <circle cx="60" cy="60" r="26" fill="#ffd166" opacity={0.15 + 0.85 * glow} />
          <circle cx="60" cy="60" r="26" fill="none" stroke="#e8e6e1" strokeWidth="2" />
        </svg>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-lg">
          <dt className="opacity-60">Voltage</dt>
          <dd>{state?.circuit.source_voltage.toFixed(1) ?? '–'} V</dd>
          <dt className="opacity-60">Current</dt>
          <dd>{state?.circuit.total_current.toFixed(2) ?? '–'} A</dd>
          <dt className="opacity-60">Circuit</dt>
          <dd>{state?.circuit.status ?? '–'}</dd>
          <dt className="opacity-60">Pulse</dt>
          <dd className="flex items-center gap-2">
            {state?.probe.pulse_hz.toFixed(1) ?? '–'} Hz
            <span className={`h-3 w-3 rounded-full ${flash ? 'bg-amber-300' : 'bg-white/15'}`} />
          </dd>
        </dl>
      </section>
      <p className="opacity-60">Scroll the mouse wheel to change the voltage.</p>

      <section className="rounded-xl bg-white/5 p-6">
        <p className="text-lg">{state?.tutor.prompt}</p>
        <div className="mt-3 flex gap-3">
          {state?.tutor.choices.map((choice) => (
            <button
              key={choice}
              className="rounded-lg bg-white/10 px-4 py-2 hover:bg-white/20"
              onClick={() => send({ type: 'answer', choice, via: 'button' })}
            >
              {choice}
            </button>
          ))}
        </div>
      </section>

      <section className="flex flex-wrap items-center gap-3 rounded-xl bg-white/5 p-6">
        <span className="opacity-60">Haptics</span>
        <select
          className="rounded bg-white/10 px-2 py-1"
          value={driverName}
          onChange={(event) => setDriverName(event.target.value as DriverName)}
        >
          {Object.keys(DRIVERS).map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
        <button className="rounded bg-white/10 px-3 py-1 hover:bg-white/20" onClick={connectDriver}>
          Connect
        </button>
        {Array.from({ length: MAX_WAVEFORM_INDEX + 1 }, (_, index) => (
          <button
            key={index}
            className="rounded bg-white/10 px-2 py-1 text-sm hover:bg-white/20"
            onClick={() => driver.playRaw(index)}
          >
            {index}
          </button>
        ))}
        {driverError && <span className="text-rose-400">{driverError}</span>}
      </section>
    </main>
  )
}
