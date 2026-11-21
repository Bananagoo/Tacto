import { Leads } from './Leads'

const PLATE_GAP = 22

/**
 * A cell: the long thin plate is positive, the short thick one negative. Current is signed
 * a -> b and leaves a battery by its positive end, so the positive plate faces `b`.
 */
export function Battery({ length }: { length: number }) {
  const centre = length / 2
  const negative = centre - PLATE_GAP / 2
  const positive = centre + PLATE_GAP / 2
  return (
    <>
      <Leads length={length} bodyWidth={PLATE_GAP} />
      <line x1={negative} y1={-20} x2={negative} y2={20} strokeWidth={14} strokeLinecap="butt" />
      <line x1={positive} y1={-40} x2={positive} y2={40} />
      <path d={`M ${positive + 18} -34 h 20 m -10 -10 v 20`} strokeWidth={4} />
    </>
  )
}
