import { createContext, useContext } from 'react'
import type { HapticsDriver } from './driver'

export interface Haptics {
  /** The one driver every haptic call goes through. */
  driver: HapticsDriver
  /** `off` means the stand-in console driver is in use and nothing reaches a mouse. */
  mouse: 'off' | 'connecting' | 'on'
  /** Why the last attempt to connect failed; empty when it did not. */
  mouseError: string
  /** Must be called from a click: the browser only opens the device picker for one. */
  connectMouse: () => void
}

export const HapticsContext = createContext<Haptics | null>(null)

export function useHaptics(): Haptics {
  const haptics = useContext(HapticsContext)
  if (!haptics) throw new Error('useHaptics needs a HapticsProvider above it')
  return haptics
}
