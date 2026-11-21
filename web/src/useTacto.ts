import { useEffect, useRef } from 'react'
import { create } from 'zustand'
import type { ClientMessage, HapticPattern, ServerMessage, State } from './contract'

interface Store {
  connected: boolean
  state: State | null
  send: (msg: ClientMessage) => void
}

export const useTacto = create<Store>(() => ({
  connected: false,
  state: null,
  send: () => {},
}))

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
      socket.onopen = () =>
        useTacto.setState({
          connected: true,
          send: (msg) => socket?.readyState === WebSocket.OPEN && socket.send(JSON.stringify(msg)),
        })
      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data) as ServerMessage
        if (msg.type === 'state') useTacto.setState({ state: msg })
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
