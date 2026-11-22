import type { Part } from '../contract'
import { dotToPoint } from './grid'

// The battery drawing (parts/Battery.tsx) is 1.6 times as long as its two dots are apart and
// about 0.69 of that gap across. The tag sits this far clear of it, on its left.
const DRAWING_LENGTH_PER_GAP = 1.6
const DRAWING_WIDTH_PER_GAP = 0.69
const GAP = 14
const WIDTH = 96
const HEIGHT = 44

/**
 * The battery's voltage, written on a tag beside it: what the scroll wheel has set. It changes
 * as the wheel turns, so the learner sees the number they are dialling. Upright whichever way
 * the battery lies.
 */
export function VoltageTag({ battery, volts }: { battery: Part; volts: number }) {
  const a = dotToPoint(battery.a)
  const b = dotToPoint(battery.b)
  const gap = Math.hypot(b.x - a.x, b.y - a.y)
  const across = a.y === b.y // lying left to right, or standing up and down
  // Half of what the drawing takes up from left to right, whichever way it lies. The tag sits
  // that far, and a little more, to the left of the battery's middle.
  const halfWide = ((across ? DRAWING_LENGTH_PER_GAP : DRAWING_WIDTH_PER_GAP) * gap) / 2
  const x = (a.x + b.x) / 2 - halfWide - GAP - WIDTH / 2
  const y = (a.y + b.y) / 2
  return (
    <g
      transform={`translate(${x} ${y})`}
      pointerEvents="none"
      aria-label={`Battery, ${volts} volts`}
    >
      <rect
        x={-WIDTH / 2}
        y={-HEIGHT / 2}
        width={WIDTH}
        height={HEIGHT}
        rx={12}
        className="fill-stone-900/85 stroke-amber-300"
        strokeWidth={3}
      />
      <text
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-amber-200 font-bold"
        fontSize={28}
      >
        {volts.toFixed(1)} V
      </text>
    </g>
  )
}
