import { useHaptics } from '../haptics/useHaptics'
import { useTacto } from '../useTacto'

/**
 * The instrument's switches: the mouse, and a warning when the server is away. Compact, for
 * the top bar, so the mat and the notebook below get the height.
 */
export function StatusBar() {
  const connected = useTacto((store) => store.connected)

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-lg">
      {/* Said only when something is wrong: a connection that is up needs no words. The mark and
          the words, not colour alone, carry it. */}
      {!connected && <span className="font-bold text-amber-300">○ Reconnecting…</span>}
      <MouseStatus />
    </div>
  )
}

const BUTTON =
  'cursor-pointer rounded-lg bg-white/15 px-3 py-1 font-semibold hover:bg-white/25 focus-visible:outline-4 focus-visible:outline-sky-300 disabled:cursor-default disabled:opacity-40'

const MOUSE_WORDS = {
  off: '○ Mouse not connected',
  connecting: '○ Connecting…',
  on: '● Mouse connected',
} as const

function MouseStatus() {
  const { mouse, mouseError, connectMouse } = useHaptics()
  return (
    <span className="flex flex-wrap items-center gap-3">
      <span className="text-stone-300">{MOUSE_WORDS[mouse]}</span>
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
