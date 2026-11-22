import batteryOffUrl from '../../assets/BatteryOff.png'
import batteryOnUrl from '../../assets/BatteryOn.png'

// Both drawings are 384 x 890, standing up, with the positive end on top.
const ASPECT = 384 / 890
// Drawn this many times longer than the two dots are apart, so it reads as the power source and
// not as one more small part. It covers a little of the wire at each end.
const SIZE_PER_LENGTH = 1.6

/**
 * A battery: the lit drawing while current flows through it, the plain one when none does,
 * whether the loop is open or the wheel is at 0 V. On a short it is lit: it is sending all it
 * can. It lies along the part's two dots with the positive end at `a`, which is where the
 * contract puts a battery's positive terminal, and is a little longer than the two dots are
 * apart.
 */
export function Battery({ length, live }: { length: number; live: boolean }) {
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
