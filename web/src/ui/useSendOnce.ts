import { useCallback, useEffect, useRef, useState } from 'react'
import type { ClientMessage } from '../contract'
import { useTacto } from '../useTacto'

// How long to wait for the lesson to move on before letting the learner press again. Long
// enough that a double click never sends twice, short enough that a lost message does not
// leave the lesson stuck.
// TODO(front end owner): check against the real session loop's response time.
const RETRY_AFTER_MS = 2000

/**
 * Send at most one message per moment of the lesson. `moment` names the point the lesson is
 * at (step and phase); once a message has gone out, further sends are dropped until the
 * moment changes or the wait runs out.
 */
export function useSendOnce(moment: string) {
  const [sentIn, setSentIn] = useState<string | null>(null)
  // The ref is what stops a second click that lands before React has re-rendered.
  const sentInRef = useRef<string | null>(null)

  useEffect(() => {
    if (sentIn === null) return
    const timer = setTimeout(() => {
      sentInRef.current = null
      setSentIn(null)
    }, RETRY_AFTER_MS)
    return () => clearTimeout(timer)
  }, [sentIn])

  const sendOnce = useCallback(
    (message: ClientMessage) => {
      if (sentInRef.current === moment) return
      sentInRef.current = moment
      setSentIn(moment)
      useTacto.getState().send(message)
    },
    [moment],
  )

  return { waiting: sentIn === moment, sendOnce }
}
