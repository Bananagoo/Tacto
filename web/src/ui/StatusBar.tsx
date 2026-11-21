import { useHaptics } from '../haptics/useHaptics'
import { useTacto } from '../useTacto'

/** The instrument's readouts: is the server there, what the wheel is set to, is the mouse on. */
export function StatusBar() {
  const connected = useTacto((store) => store.connected)
  const sourceVoltage = useTacto((store) => store.state?.circuit.source_voltage)

  return (
    <footer className="flex flex-wrap items-center justify-between gap-x-10 gap-y-3 rounded-3xl bg-white/5 px-8 py-4 text-2xl">
      {/* A filled or hollow mark and the words: the state is not carried by colour. */}
      <span className={connected ? 'text-stone-100' : 'font-bold text-amber-300'}>
        {connected ? '● Connected' : '○ Reconnecting…'}
      </span>
      <span className="flex items-baseline gap-4">
        <span className="text-stone-300">Voltage (scroll the wheel)</span>
        <span className="text-5xl font-bold tabular-nums">
          {sourceVoltage === undefined ? '–' : sourceVoltage.toFixed(1)} V
        </span>
      </span>
      <MouseStatus />
    </footer>
  )
}

const MOUSE_WORDS = {
  off: '○ Mouse not connected',
  connecting: '○ Connecting…',
  on: '● Mouse connected',
} as const

function MouseStatus() {
  const { mouse, mouseError, connectMouse } = useHaptics()
  return (
    <span className="flex flex-wrap items-center gap-4">
      <span>{MOUSE_WORDS[mouse]}</span>
      {mouse !== 'on' && (
        <button
          type="button"
          disabled={mouse === 'connecting'}
          onClick={connectMouse}
          className="cursor-pointer rounded-xl bg-white/15 px-5 py-2 font-semibold hover:bg-white/25 focus-visible:outline-4 focus-visible:outline-sky-300 disabled:cursor-default disabled:opacity-40"
        >
          Connect mouse
        </button>
      )}
      {mouseError && (
        <span role="alert" className="font-bold text-amber-300">
          {mouseError}
        </span>
      )}
    </span>
  )
}
