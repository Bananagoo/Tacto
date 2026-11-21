import { Leads } from './Leads'

const GAP = 70
const OPEN_ANGLE_DEG = -32

interface SwitchProps {
  length: number
  closed: boolean
}

/** A switch: the lever lies across the gap when closed and lifts clear of it when open. */
export function Switch({ length, closed }: SwitchProps) {
  const hinge = (length - GAP) / 2
  return (
    <>
      <Leads length={length} bodyWidth={GAP} />
      <circle cx={hinge} cy={0} r={8} className="fill-stone-100" />
      <circle cx={hinge + GAP} cy={0} r={8} className="fill-stone-100" />
      {/* The lever is drawn from the hinge so that it turns about the hinge. */}
      <g transform={`translate(${hinge} 0)`}>
        <line
          x1={0}
          y1={0}
          x2={GAP}
          y2={0}
          className="transition-transform duration-200 ease-out"
          style={{ transform: `rotate(${closed ? 0 : OPEN_ANGLE_DEG}deg)` }}
        />
      </g>
    </>
  )
}
