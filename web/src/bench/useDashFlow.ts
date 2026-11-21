import { useEffect, useRef, type RefObject } from 'react'
import { DASH_PERIOD } from './flow'

// At playback rate 1 the dashes travel one period in this long.
const BASE_DURATION_MS = 1000

/**
 * Slide a dashed line's dashes along it at `speed` SVG units per second; the sign picks the
 * direction. The animation is made once per direction and only its playback rate follows
 * the speed, so a changing current speeds the dashes up or down without a jump or restart.
 */
export function useDashFlow(lineRef: RefObject<SVGLineElement | null>, speed: number) {
  const direction = Math.sign(speed)
  const animationRef = useRef<Animation | null>(null)

  useEffect(() => {
    const line = lineRef.current
    if (!line || direction === 0) return
    // A falling dash offset moves the dashes from the line's start towards its end.
    const animation = line.animate(
      [{ strokeDashoffset: 0 }, { strokeDashoffset: -direction * DASH_PERIOD }],
      { duration: BASE_DURATION_MS, iterations: Infinity },
    )
    animationRef.current = animation
    return () => {
      animation.cancel()
      animationRef.current = null
    }
  }, [lineRef, direction])

  // Declared after the effect above so that a new animation gets its rate straight away.
  useEffect(() => {
    if (animationRef.current) animationRef.current.playbackRate = Math.abs(speed) / DASH_PERIOD
  }, [speed, direction])
}
