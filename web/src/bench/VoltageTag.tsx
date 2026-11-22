import type { Part } from '../contract'
import { dotToPoint } from './grid'

// How far the tag sits from the battery's middle, beside it rather than on it: the battery
// drawing is about 70 across (a dot pitch is 100).
const OFFSET = 62
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
  const across = a.y === b.y // lying left to right: the tag goes below it, else to its right
  const x = (a.x + b.x) / 2 + (across ? 0 : OFFSET + WIDTH / 2 - 20)
  const y = (a.y + b.y) / 2 + (across ? OFFSET : 0)
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
