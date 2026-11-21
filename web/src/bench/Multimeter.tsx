import multimeterUrl from '../assets/Multimeter.png'
import type { Point } from './grid'
import type { Reading } from './readingAt'

// The drawing is 608 x 842 and its red probe tip is at (340, 815). It is drawn at WIDTH_UNITS
// across, positioned so that tip lands on the pointer: the multimeter is the mouse's cursor.
const WIDTH_UNITS = 100
// The readout's sizes were set at 170 wide, so they follow the drawing's size.
const TEXT = WIDTH_UNITS / 170
const SCALE = WIDTH_UNITS / 608
const HEIGHT_UNITS = 842 * SCALE
const TIP = { x: 340 * SCALE, y: 815 * SCALE }
// The screen's middle in the drawing, and how far the drawing tilts it.
const SCREEN = { x: 290 * SCALE, y: 218 * SCALE }
const SCREEN_TILT_DEG = -4

interface MultimeterProps {
  /** Where the pointer is on the mat, in SVG units; null when it is off the mat. */
  point: Point | null
  /** What is under the tip; null over nothing. */
  reading: Reading | null
}

/**
 * The multimeter, drawn as the mouse's pointer. Its tip is the pointer, and its screen reads
 * the amps and the volts across what the tip touches (a wire has almost none). The vibration
 * is the current; the volts here are across a part, not the wheel's battery setting.
 */
export function Multimeter({ point, reading }: MultimeterProps) {
  if (!point) return null
  return (
    <g transform={`translate(${point.x} ${point.y})`} pointerEvents="none">
      <image
        href={multimeterUrl}
        x={-TIP.x}
        y={-TIP.y}
        width={WIDTH_UNITS}
        height={HEIGHT_UNITS}
        aria-label="The multimeter"
      />
      <g
        transform={`translate(${-TIP.x + SCREEN.x} ${-TIP.y + SCREEN.y}) rotate(${SCREEN_TILT_DEG})`}
        textAnchor="middle"
        fontWeight={700}
        className="fill-stone-800 tabular-nums"
      >
        {reading?.short ? (
          <text y={8 * TEXT} fontSize={19 * TEXT}>
            SHORT
          </text>
        ) : (
          <>
            <text y={-4 * TEXT} fontSize={19 * TEXT}>
              {reading ? `${reading.current.toFixed(2)} A` : '-- A'}
            </text>
            <text y={17 * TEXT} fontSize={19 * TEXT}>
              {reading ? `${reading.volts.toFixed(1)} V` : '-- V'}
            </text>
          </>
        )}
      </g>
    </g>
  )
}
