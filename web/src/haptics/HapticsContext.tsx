import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { DRIVERS, type HapticsDriver } from './driver'
import { HapticsContext, type Haptics } from './useHaptics'

/**
 * Owns the one haptics driver. The page starts on the console driver, so the whole lesson
 * runs with no mouse; a click on "Connect mouse" swaps in the WebHID driver.
 */
export function HapticsProvider({ children }: { children: ReactNode }) {
  const [driver, setDriver] = useState<HapticsDriver>(DRIVERS.console)
  const [connecting, setConnecting] = useState(false)
  const [mouseError, setMouseError] = useState('')
  // A ref as well as the state, so a second click before the re-render opens no second picker.
  const connectingRef = useRef(false)

  // Let go of a driver when it is replaced and when the page goes away.
  useEffect(() => () => driver.close(), [driver])

  const connectMouse = useCallback(async () => {
    if (connectingRef.current) return
    connectingRef.current = true
    setConnecting(true)
    setMouseError('')
    const mouse = DRIVERS.webhid()
    try {
      await mouse.connect()
      setDriver(mouse)
      // So the person holding the mouse knows it worked without looking up.
      mouse.play('tick')
    } catch (error) {
      // The console driver stays in use, so the lesson carries on without the mouse.
      mouse.close()
      setMouseError(error instanceof Error ? error.message : String(error))
    } finally {
      connectingRef.current = false
      setConnecting(false)
    }
  }, [])

  const haptics = useMemo<Haptics>(
    () => ({
      driver,
      mouse: connecting ? 'connecting' : driver.name === 'webhid' ? 'on' : 'off',
      mouseError,
      connectMouse,
    }),
    [driver, connecting, mouseError, connectMouse],
  )

  return <HapticsContext value={haptics}>{children}</HapticsContext>
}
