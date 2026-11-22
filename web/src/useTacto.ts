import { useEffect, useRef } from 'react'
import { create } from 'zustand'
import type { ClientMessage, HapticPattern, ServerState, State } from './contract'
import { fromServer } from './fromServer'

interface Store {
  connected: boolean
  state: State | null
  voltageInputEpoch: number
  send: (msg: ClientMessage) => void
}

export const useTacto = create<Store>(() => ({
  connected: false,
  state: null,
  voltageInputEpoch: 0,
  send: () => {},
}))

// The mode the opening page asked for (the circuit board: Tinker; the play button: Lab). It is
// sent once, as soon as the lab is connected, and then forgotten, so a reconnect later does
// not restart the lesson.
let openingMode: 'tinker' | 'lab' | null = null

export function openIn(mode: 'tinker' | 'lab') {
  openingMode = mode
  // Already connected (back from the opening page with the lab still open): send it now.
  const { connected, send } = useTacto.getState()
  if (connected) {
    send({ type: 'set_mode', mode })
    openingMode = null
  }
}

/** Open the WebSocket once, at the top of the app. Reconnects on its own. */
export function useTactoConnection(onHaptic: (pattern: HapticPattern) => void) {
  // Kept in a ref so that a new handler (for example after the mouse connects and the
  // haptics driver changes) does not close and reopen the socket.
  const onHapticRef = useRef(onHaptic)
  useEffect(() => {
    onHapticRef.current = onHaptic
  }, [onHaptic])

  useEffect(() => {
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let closed = false

    const open = () => {
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
      // ?learner=<nickname> on the page picks whose progress is loaded; there is no login.
      const learner = new URLSearchParams(location.search).get('learner')
      const query = learner ? `?learner=${encodeURIComponent(learner)}` : ''
      socket = new WebSocket(`${scheme}://${location.host}/ws${query}`)
      socket.onopen = () => {
        useTacto.setState({
          connected: true,
          send: (msg) => {
            if (socket?.readyState !== WebSocket.OPEN) return
            // Forget the wheel's accumulated target when starting a new demonstration.
            if (msg.type === 'restart_lesson' || (msg.type === 'set_mode' && msg.mode === 'lab'))
              useTacto.setState((store) => ({ voltageInputEpoch: store.voltageInputEpoch + 1 }))
            socket.send(JSON.stringify(msg))
          },
        })
        if (openingMode !== null) {
          useTacto.getState().send({ type: 'set_mode', mode: openingMode })
          openingMode = null
        }
      }
      socket.onmessage = (event) => {
        // The server sends one kind of message, the state. One-off haptic patterns are no
        // longer sent; `onHaptic` stays for the day they are.
        const msg = JSON.parse(event.data) as
          ServerState | { type: 'haptic'; pattern: HapticPattern }
        if (msg.type === 'state') useTacto.setState({ state: fromServer(msg) })
        else if (msg.type === 'haptic') onHapticRef.current(msg.pattern)
      }
      socket.onclose = () => {
        // A socket closed by the cleanup below reports late, possibly after its replacement
        // has opened; it must not mark the new connection as lost.
        if (closed) return
        useTacto.setState({ connected: false })
        retry = setTimeout(open, 500)
      }
    }

    open()
    return () => {
      closed = true
      clearTimeout(retry)
      socket?.close()
      useTacto.setState({ connected: false })
    }
  }, [])
}
