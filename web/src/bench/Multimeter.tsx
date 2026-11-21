import multimeterUrl from '../assets/Multimeter.png'
import type { Point } from './grid'

// The drawing is 608 x 842 and its red probe tip is at (340, 815). It is drawn at WIDTH_UNITS
// across, positioned so that tip lands on the pointer: the multimeter is the mouse's cursor.
const WIDTH_UNITS = 100
const SCALE = WIDTH_UNITS / 608
const HEIGHT_UNITS = 842 * SCALE
const TIP = { x: 340 * SCALE, y: 815 * SCALE }

/**
 * The multimeter, drawn as the mouse's pointer. Its tip is the pointer. What the tip reads is
 * shown by `Readout`, in the corner, not on the drawing's own screen.
 */
export function Multimeter({ point }: { point: Point | null }) {
  if (!point) return null
  return (
    <image
      href={multimeterUrl}
      x={point.x - TIP.x}
      y={point.y - TIP.y}
      width={WIDTH_UNITS}
      height={HEIGHT_UNITS}
      pointerEvents="none"
      aria-label="The multimeter"
    />
  )
}
