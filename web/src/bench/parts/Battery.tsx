import batteryOffUrl from '../../assets/BatteryOff.png'
import batteryOnUrl from '../../assets/BatteryOn.png'
import { useTacto } from '../../useTacto'

// Both drawings are 384 x 890, standing up, with the positive end on top.
const ASPECT = 384 / 890
// Drawn this many times longer than the two dots are apart, so it reads as the power source and
// not as one more small part. It covers a little of the wire at each end.
const SIZE_PER_LENGTH = 1.6

/**
 * A battery: the lit drawing while the wheel gives it voltage, the plain one at 0 V. It lies
 * along the part's two dots with the positive end at `a`, which is where the contract puts a
 * battery's positive terminal, and is a little longer than the two dots are apart.
 */
export function Battery({ length }: { length: number }) {
  // A true or false, not the voltage: this part draws again only when the wheel crosses 0 V.
  const live = useTacto((store) => (store.state?.circuit.source_voltage ?? 0) > 0)
  const size = length * SIZE_PER_LENGTH
  const width = size * ASPECT
  return (
    // Turned a quarter turn so the drawing's top (the positive end) points back along the part.
    <g transform={`translate(${length / 2} 0) rotate(-90)`}>
      <image
        href={live ? batteryOnUrl : batteryOffUrl}
        x={-width / 2}
        y={-size / 2}
        width={width}
        height={size}
        aria-label={live ? 'Battery, on' : 'Battery, off'}
      />
    </g>
  )
}
