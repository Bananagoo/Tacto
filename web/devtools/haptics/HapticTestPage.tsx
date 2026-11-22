// Dev-only page (not the product UI): pick a driver, Connect, fire one waveform, or repeat the
// selected waveform at a chosen rate to find the fastest rate that still feels like separate ticks
// (the value for MAX_PULSE_HZ in usePulse.ts). The strength slider changes how hard the mouse
// vibrates; it is a setting stored on the mouse, so it is sent when the slider is released.
// Served at /devtools/#haptics. It reuses DRIVERS from src/haptics/driver.ts so there is
// one code path to the mouse. The `console` driver needs no hardware (flashes a dot instead).

import { useEffect, useMemo, useState } from 'react'
import {
  allowedMice,
  DRIVERS,
  MAX_WAVEFORM_INDEX,
  onMousePlugged,
  WebHidHaptics,
  type DriverName,
} from '../../src/haptics/driver'

const MIN_RATE_HZ = 1
const MAX_RATE_HZ = 30

/**
 * The mouse connection test. The lab connects to the mouse on its own, but only to one the
 * browser was allowed once: this is where that is done, and where it is checked before a demo.
 */
function MouseConnection() {
  const [allowed, setAllowed] = useState<number | null>(null)
  const [result, setResult] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const look = () => void allowedMice().then(setAllowed)
    look()
    return onMousePlugged(look)
  }, [])

  const attempt = async (how: 'allow' | 'test') => {
    setBusy(true)
    setResult('')
    const mouse = new WebHidHaptics()
    try {
      if (how === 'allow') await mouse.connect()
      else await mouse.connectKnown()
      mouse.play('tick')
      const strength = await mouse.getStrength()
      setResult(
        `✓ Connected without a click${how === 'allow' ? ' from now on' : ''}: you should have felt one tick. Strength setting ${strength ?? 'unknown'}%.`,
      )
    } catch (error) {
      setResult(`✗ ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      mouse.close()
      setAllowed(await allowedMice())
      setBusy(false)
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-3xl bg-white/5 p-6">
      <h2 className="m-0 font-['Patrick_Hand'] text-3xl text-stone-100">Mouse connection</h2>
      <p className="m-0 text-stone-300">
        The lab connects to the MX Master 4 by itself at start and after it is switched on or
        plugged in, once this browser has been allowed to use it. Allow it once here; the browser
        remembers.
      </p>
      <p className={`m-0 text-lg ${allowed ? 'text-emerald-300' : 'text-amber-200'}`}>
        {allowed === null
          ? 'Checking…'
          : allowed
            ? `✓ Allowed (${allowed} device${allowed === 1 ? '' : 's'}): the lab will connect on its own.`
            : '! Not allowed yet: press Allow the mouse and pick the USB Receiver or the MX Master 4.'}
      </p>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={() => void attempt('allow')}
          className="rounded-2xl bg-white/10 px-5 py-2 text-lg hover:bg-white/20 disabled:opacity-50"
        >
          Allow the mouse
        </button>
        <button
          type="button"
          disabled={busy || !allowed}
          onClick={() => void attempt('test')}
          className="rounded-2xl bg-emerald-500 px-5 py-2 text-lg text-emerald-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          Test the connection
        </button>
      </div>
      {result && <p className="m-0 text-stone-100">{result}</p>}
      <p className="m-0 text-sm text-stone-400">
        The test connects the way the lab does (no picker), plays one tick, and lets go. If the lab
        is open in another tab it may hold the mouse: close it for the test.
      </p>
    </section>
  )
}

/** Does the thumb wheel reach the browser? It turns the multimeter's dial in the lab. */
function ThumbWheel() {
  const [seen, setSeen] = useState({ sideways: 0, upDown: 0, last: '' })
  useEffect(() => {
    const onWheel = (event: WheelEvent) =>
      setSeen((before) =>
        Math.abs(event.deltaX) > Math.abs(event.deltaY)
          ? {
              ...before,
              sideways: before.sideways + 1,
              last: `sideways ${event.deltaX > 0 ? 'right' : 'left'} (${event.deltaX.toFixed(0)})`,
            }
          : {
              ...before,
              upDown: before.upDown + 1,
              last: `up/down (${event.deltaY.toFixed(0)})`,
            },
      )
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => window.removeEventListener('wheel', onWheel)
  }, [])
  return (
    <section className="flex flex-col gap-2 rounded-3xl bg-white/5 p-6">
      <h2 className="m-0 font-['Patrick_Hand'] text-3xl text-stone-100">Thumb wheel</h2>
      <p className="m-0 text-stone-300">
        Roll the thumb wheel on the side of the mouse. It turns the multimeter's dial in the lab;
        the main wheel is the voltage.
      </p>
      <p
        className={`m-0 text-lg ${seen.sideways ? 'text-emerald-300' : 'text-amber-200'}`}
        role="status"
      >
        {seen.sideways
          ? `✓ Thumb wheel seen (${seen.sideways} events). Last: ${seen.last}`
          : seen.upDown
            ? `! Only up/down scrolling seen (last: ${seen.last}). If that was the thumb wheel, Logi Options+ has it set to something else: set it to horizontal scroll.`
            : 'Waiting for the thumb wheel…'}
      </p>
    </section>
  )
}

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
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-8">
      <MouseConnection />
      <ThumbWheel />
      <h1 className="m-0 mt-4 font-['Patrick_Hand'] text-3xl font-normal">Waveform test</h1>
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
