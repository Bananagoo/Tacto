import type { Point } from './grid'
import { SKIP_IN_SCREENSHOT } from './screenshot'

/**
 * The multimeter's red probe tip, drawn as the mouse's pointer while the meter is picked up.
 * The meter itself sits large on the bench (`BenchMeter`) and shows what the tip reads.
 */
export function Probe({ point }: { point: Point | null }) {
  if (!point) return null
  return (
    <g pointerEvents="none" {...{ [SKIP_IN_SCREENSHOT]: true }} aria-label="The multimeter's probe">
      <line
        x1={point.x}
        y1={point.y}
        x2={point.x + 26}
        y2={point.y - 44}
        className="stroke-red-700"
        strokeWidth={12}
        strokeLinecap="round"
      />
      <circle
        cx={point.x}
        cy={point.y}
        r={9}
        className="fill-red-600 stroke-white"
        strokeWidth={4}
      />
    </g>
  )
}
