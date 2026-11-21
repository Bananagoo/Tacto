import { memo } from 'react'
import { dotToPoint } from './grid'

interface WireLineProps {
  // Plain numbers, not the wire object: every state message carries new objects, and
  // numbers let memo skip a wire that has not changed.
  aCol: number
  aRow: number
  bCol: number
  bRow: number
}

/** One drawn wire between two dots. */
export const WireLine = memo(function WireLine({ aCol, aRow, bCol, bRow }: WireLineProps) {
  const a = dotToPoint([aCol, aRow])
  const b = dotToPoint([bCol, bRow])
  return (
    <line
      x1={a.x}
      y1={a.y}
      x2={b.x}
      y2={b.y}
      className="stroke-stone-100/30"
      strokeWidth={6}
      strokeLinecap="round"
    />
  )
})
