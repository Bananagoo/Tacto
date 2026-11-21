import { useEffect } from 'react'
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
  useEffect(() => {
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let closed = false

    const open = () => {
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
      socket = new WebSocket(`${scheme}://${location.host}/ws`)
      socket.onopen = () =>
        useTacto.setState({
          connected: true,
          send: (msg) => socket?.readyState === WebSocket.OPEN && socket.send(JSON.stringify(msg)),
        })
      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data) as ServerMessage
        if (msg.type === 'state') useTacto.setState({ state: msg })
        else if (msg.type === 'haptic') onHaptic(msg.pattern)
      }
      socket.onclose = () => {
        useTacto.setState({ connected: false })
        if (!closed) retry = setTimeout(open, 500)
      }
    }

    open()
    return () => {
      closed = true
      clearTimeout(retry)
      socket?.close()
    }
  }, [onHaptic])
}
