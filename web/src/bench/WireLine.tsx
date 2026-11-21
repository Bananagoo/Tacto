import { memo, useRef } from 'react'
import { DASH_ARRAY, flowSpeed } from './flow'
import { dotToPoint } from './grid'
import { useDashFlow } from './useDashFlow'

interface WireLineProps {
  // Plain numbers, not the wire object: every state message carries new objects, and
  // numbers let memo skip a wire that has not changed.
  aCol: number
  aRow: number
  bCol: number
  bRow: number
  /** Amps, signed a -> b. */
  current: number
  overloaded: boolean
  /** The multimeter is on this wire. */
  touched: boolean
}

/**
 * One drawn wire. Dead: a dim line. Carrying current: dashes run along it, faster for more
 * current, in the direction it flows. Overloaded: more than twice as thick, hot orange and
 * pulsing, so a shorted path stands out by shape and movement as well as colour. Under the
 * multimeter: a wide white halo behind it, so the room sees which wire it is reading.
 */
export const WireLine = memo(function WireLine({
  aCol,
  aRow,
  bCol,
  bRow,
  current,
  overloaded,
  touched,
}: WireLineProps) {
  const a = dotToPoint([aCol, aRow])
  const b = dotToPoint([bCol, bRow])
  const ends = { x1: a.x, y1: a.y, x2: b.x, y2: b.y }

  const speed = flowSpeed(current)
  const flowRef = useRef<SVGLineElement>(null)
  useDashFlow(flowRef, speed)

  return (
    <g strokeLinecap="round">
      {touched && <line {...ends} className="stroke-white/70" strokeWidth={26} />}
      <line
        {...ends}
        className={overloaded ? 'animate-overload stroke-orange-500' : 'stroke-amber-200/50'}
        strokeWidth={overloaded ? 16 : 6}
      />
      {speed !== 0 && (
        <line
          ref={flowRef}
          {...ends}
          className={overloaded ? 'stroke-white' : 'stroke-sky-300'}
          strokeWidth={6}
          strokeDasharray={DASH_ARRAY}
        />
      )}
    </g>
  )
})
