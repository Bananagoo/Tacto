import { memo } from 'react'
import { dotToPoint, GRID_COLS, GRID_ROWS, type Point } from './grid'

// The grid never changes while the page is open, so its points are worked out once.
const DOTS: Point[] = Array.from({ length: GRID_COLS * GRID_ROWS }, (_, index) =>
  dotToPoint([index % GRID_COLS, Math.floor(index / GRID_COLS)]),
)

/** The printed mat's dots: a quiet backdrop that shows where parts and wires can go. */
export const DotGrid = memo(function DotGrid() {
  return (
    <g className="fill-stone-100/30">
      {DOTS.map(({ x, y }) => (
        <circle key={`${x},${y}`} cx={x} cy={y} r={5} />
      ))}
    </g>
  )
})
