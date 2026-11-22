import resistorUrl from '../../assets/Resistor.png'

// The picture is about 4 wide to 1 high, with a wire out of each end, so it is drawn as wide as
// the part is long and the wire tips reach the two dots.
const HEIGHT_PER_LENGTH = 0.25

/** A resistor: the blue body with its colour bands, and a wire out of each end. */
export function Resistor({ length }: { length: number }) {
  const height = length * HEIGHT_PER_LENGTH
  return (
    <image
      href={resistorUrl}
      x={0}
      y={-height / 2}
      width={length}
      height={height}
      preserveAspectRatio="xMidYMid meet"
      aria-label="Resistor"
    />
  )
}
