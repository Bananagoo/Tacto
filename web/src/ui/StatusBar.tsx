import { useHaptics } from '../haptics/useHaptics'
import { useTacto } from '../useTacto'

/** Along the bottom: the way back home, the mouse, and a warning when the server is away. */
export function StatusBar({ onHome }: { onHome: () => void }) {
  const connected = useTacto((store) => store.connected)

  return (
    <footer className="flex flex-wrap items-center justify-between gap-x-10 gap-y-3 rounded-3xl bg-white/5 px-8 py-4 text-2xl">
      <button
        type="button"
        onClick={onHome}
        className="flex cursor-pointer items-center gap-3 rounded-xl border-4 border-stone-100/40 px-5 py-2 text-xl font-semibold text-stone-100 hover:border-stone-100 focus-visible:outline-4 focus-visible:outline-sky-300"
      >
        <span className="text-3xl leading-none" aria-hidden="true">
          ←
        </span>
        Home
      </button>
      {/* Said only when something is wrong: a connection that is up needs no words. The mark and
          the words, not colour alone, carry it. */}
      {!connected && <span className="font-bold text-amber-300">○ Reconnecting…</span>}
      <div className="ml-auto">
        <MouseStatus />
      </div>
    </footer>
  )
}

const BUTTON =
  'cursor-pointer rounded-xl bg-white/15 px-5 py-2 font-semibold hover:bg-white/25 focus-visible:outline-4 focus-visible:outline-sky-300 disabled:cursor-default disabled:opacity-40'

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
          className={BUTTON}
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
