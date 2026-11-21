// Dev-only page (not the product UI): pick a driver, Connect, fire one waveform, or repeat the
// selected waveform at a chosen rate to find the fastest rate that still feels like separate ticks
// (the value for MAX_PULSE_HZ in usePulse.ts). The strength slider changes how hard the mouse
// vibrates; it is a setting stored on the mouse, so it is sent when the slider is released.
// Served at /devtools/#haptics. It reuses DRIVERS from src/haptics/driver.ts so there is
// one code path to the mouse. The `console` driver needs no hardware (flashes a dot instead).

import { useEffect, useMemo, useState } from 'react'
import { DRIVERS, MAX_WAVEFORM_INDEX, type DriverName } from '../../src/haptics/driver'

const MIN_RATE_HZ = 1
const MAX_RATE_HZ = 30

export default function HapticTestPage() {
  const [driverName, setDriverName] = useState<DriverName>('console')
  const driver = useMemo(() => DRIVERS[driverName](), [driverName])
  const [connected, setConnected] = useState(driver.isConnected)
  const [index, setIndex] = useState(0)
  const [message, setMessage] = useState('')
  const [flash, setFlash] = useState(false)
  const [rateHz, setRateHz] = useState(8)
  const [ticking, setTicking] = useState(false)
  const [strength, setStrength] = useState<number | null>(null)

  // Release the old driver's socket or HID device when switching away.
  useEffect(() => () => driver.close(), [driver])

  // Repeats the waveform picked in the index dropdown, so candidates for `tick` can be compared
  // at one rate. Once chosen, it goes in the WAVEFORM table in driver.ts.
  useEffect(() => {
    if (!ticking || !connected) return
    const timer = setInterval(() => driver.playRaw(index), 1000 / rateHz)
    return () => clearInterval(timer)
  }, [ticking, connected, rateHz, index, driver])

  useEffect(() => {
    const onFire = () => {
      setFlash(true)
      setTimeout(() => setFlash(false), 80)
    }
    window.addEventListener('tacto:haptic', onFire)
    return () => window.removeEventListener('tacto:haptic', onFire)
  }, [])

  const run = async (action: () => void | Promise<void>) => {
    setMessage('')
    try {
      await action()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error))
    }
    setConnected(driver.isConnected)
  }

  return (
    <main className="mx-auto flex max-w-md flex-col gap-4 p-8">
      <h1 className="text-2xl font-semibold">Haptics test</h1>
      <select
        className="rounded bg-white/10 px-2 py-1"
        value={driverName}
        onChange={(event) => {
          setDriverName(event.target.value as DriverName)
          setConnected(false)
          setStrength(null)
          setMessage('')
        }}
      >
        {Object.keys(DRIVERS).map((name) => (
          <option key={name}>{name}</option>
        ))}
      </select>
      <button
        className="rounded bg-white/10 px-3 py-2 hover:bg-white/20"
        onClick={() =>
          run(async () => {
            await driver.connect()
            setStrength(await driver.getStrength())
          })
        }
      >
        Connect
      </button>
      <span className={connected ? 'text-emerald-400' : 'text-rose-400'}>
        {connected ? 'connected' : 'not connected'}
      </span>
      <div className="flex items-center gap-3">
        <select
          className="rounded bg-white/10 px-2 py-1"
          value={index}
          onChange={(event) => setIndex(Number(event.target.value))}
        >
          {Array.from({ length: MAX_WAVEFORM_INDEX + 1 }, (_, i) => (
            <option key={i}>{i}</option>
          ))}
        </select>
        <button
          className="rounded bg-white/10 px-3 py-2 hover:bg-white/20 disabled:opacity-40"
          disabled={!connected}
          onClick={() => run(() => driver.playRaw(index))}
        >
          Pulse
        </button>
        <span className={`h-3 w-3 rounded-full ${flash ? 'bg-amber-300' : 'bg-white/15'}`} />
      </div>
      <div className="flex items-center gap-3">
        <label className="flex flex-1 items-center gap-3">
          <span className="w-20 opacity-60">Speed</span>
          <input
            type="range"
            className="flex-1"
            min={MIN_RATE_HZ}
            max={MAX_RATE_HZ}
            step={1}
            value={rateHz}
            onChange={(event) => setRateHz(Number(event.target.value))}
          />
          <span className="w-14 text-right tabular-nums">{rateHz} Hz</span>
        </label>
        <button
          className="rounded bg-white/10 px-3 py-2 hover:bg-white/20 disabled:opacity-40"
          disabled={!connected}
          onClick={() => setTicking((on) => !on)}
        >
          {ticking ? 'Stop ticks' : 'Start ticks'}
        </button>
      </div>
      <label className="flex items-center gap-3">
        <span className="w-20 opacity-60">Strength</span>
        <input
          type="range"
          className="flex-1 disabled:opacity-40"
          min={0}
          max={100}
          step={5}
          disabled={!connected || !driver.canSetStrength}
          value={strength ?? 0}
          onChange={(event) => setStrength(Number(event.target.value))}
          onPointerUp={() => strength !== null && run(() => driver.setStrength(strength))}
          onKeyUp={() => strength !== null && run(() => driver.setStrength(strength))}
        />
        <span className="w-14 text-right tabular-nums">{strength ?? '–'}</span>
      </label>
      {!driver.canSetStrength && (
        <p className="text-sm opacity-60">This driver cannot change strength; use webhid.</p>
      )}
      <p className="text-sm opacity-60">
        WebHID effect ids are not confirmed to match the plugin's waveform names.
      </p>
      {message && <p className="text-rose-400">{message}</p>}
    </main>
  )
}
