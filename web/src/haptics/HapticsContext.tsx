import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { DRIVERS, onMousePlugged, PICKER_CLOSED, WebHidHaptics, type HapticsDriver } from './driver'
import { HapticsContext, type Haptics } from './useHaptics'

// While in front and without the mouse, try to connect this often.
const RETRY_MS = 2000

/**
 * Owns the one haptics driver. The page starts on the console driver, so the whole lesson
 * runs with no mouse, and connects to the mouse on its own (Katie, 22 Nov 2026): at start, and
 * again whenever a mouse or its receiver is plugged in or switched on. That needs the site to
 * have been allowed the mouse once, from Dev tools, Haptics; the browser remembers it.
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
      const words = error instanceof Error ? error.message : String(error)
      // Closing the picker is a change of mind, not an error: say nothing.
      if (words !== PICKER_CLOSED) setMouseError(words)
    } finally {
      connectingRef.current = false
      setConnecting(false)
    }
  }, [])

  // Connect on our own to a mouse the browser already allows, and keep it connected: try at
  // start and whenever a device comes or goes. Quiet when there is none: the lab runs without.
  const driverRef = useRef(driver)
  useEffect(() => {
    driverRef.current = driver
  }, [driver])
  useEffect(() => {
    let stopped = false
    const reconnect = async () => {
      const current = driverRef.current
      if (current.name === 'webhid' && current.isConnected) return
      if (current.name === 'webhid') setDriver(DRIVERS.console) // it was unplugged
      if (connectingRef.current) return
      connectingRef.current = true
      const mouse = new WebHidHaptics()
      try {
        await mouse.connectKnown()
        if (stopped) mouse.close()
        else {
          setDriver(mouse)
          setMouseError('')
          console.log('haptics: mouse connected')
        }
      } catch {
        mouse.close()
      } finally {
        connectingRef.current = false
      }
    }
    // Only one tab can hold the mouse, so a hidden tab lets go of it and takes it back when it
    // is in front again: a second lab tab (or the dev tools) never leaves the lab without it.
    const onVisibility = () => {
      if (document.hidden) {
        const current = driverRef.current
        if (current.name === 'webhid') {
          current.close()
          setDriver(DRIVERS.console)
        }
      } else void reconnect()
    }
    if (!document.hidden) void reconnect()
    const stop = onMousePlugged(() => {
      if (!document.hidden) void reconnect()
    })
    document.addEventListener('visibilitychange', onVisibility)
    // And keep trying while in front without the mouse: another tab may have held it and let
    // go without any event reaching this one (closing a tab sends none).
    const retry = setInterval(() => {
      if (!document.hidden) void reconnect()
    }, RETRY_MS)
    return () => {
      stopped = true
      stop()
      clearInterval(retry)
      document.removeEventListener('visibilitychange', onVisibility)
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
