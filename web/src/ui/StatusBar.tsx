import { useHaptics } from '../haptics/useHaptics'
import { useTacto } from '../useTacto'
import { TabButton } from './TabButton'
import tabMouse from '../assets/TabMouse.png'

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

const MOUSE_WORDS = {
  off: 'Connect mouse',
  connecting: 'Connecting…',
  on: 'Mouse on',
} as const

/** The mouse as a tab: plain until it is connected, then its blue tab. */
function MouseStatus() {
  const { mouse, mouseError, connectMouse } = useHaptics()
  return (
    <span className="flex flex-wrap items-center gap-3">
      <TabButton
        art={tabMouse}
        chosen={mouse === 'on'}
        disabled={mouse === 'connecting'}
        onClick={mouse === 'on' ? undefined : connectMouse}
        title={mouse === 'on' ? 'The mouse is connected' : 'Connect the MX Master 4'}
        label={mouse === 'on' ? 'Mouse connected' : undefined}
        long={mouse !== 'on'}
      >
        {MOUSE_WORDS[mouse]}
      </TabButton>
      {mouseError && (
        <span role="alert" className="font-bold text-amber-300">
          {mouseError}
        </span>
      )}
    </span>
  )
}
