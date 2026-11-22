import { useHaptics } from '../haptics/useHaptics'
import { useTacto } from '../useTacto'

/**
 * Warnings for the top bar: the server away, or the mouse failing. Compact, for
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

/** The mouse connects on its own (HapticsContext.tsx); only a failure is worth words here. */
function MouseStatus() {
  const { mouseError } = useHaptics()
  if (!mouseError) return null
  return (
    <span role="alert" className="font-bold text-amber-300">
      {mouseError}
    </span>
  )
}
