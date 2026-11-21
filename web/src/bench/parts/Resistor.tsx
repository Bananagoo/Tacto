import { Leads } from './Leads'

const WIDTH = 84
const PEAK = 18
const ZIGS = 6

/** The zigzag resistor symbol. */
export function Resistor({ length }: { length: number }) {
  const start = (length - WIDTH) / 2
  const step = WIDTH / ZIGS
  // Peaks sit halfway along each step and alternate sides, so the zigzag starts and ends
  // on the axis where the leads meet it.
  const peaks = Array.from(
    { length: ZIGS },
    (_, index) => `${start + (index + 0.5) * step},${index % 2 === 0 ? -PEAK : PEAK}`,
  )
  return (
    <>
      <Leads length={length} bodyWidth={WIDTH} />
      <polyline
        points={`${start},0 ${peaks.join(' ')} ${start + WIDTH},0`}
        strokeLinejoin="round"
      />
    </>
  )
}
