import switchOffUrl from '../../assets/SwitchOff.png'
import switchOnUrl from '../../assets/SwitchOn.png'
import { Leads } from './Leads'

// The switch is drawn this wide (a dot pitch is 100). The pictures have no wires, so a plain lead
// joins each dot to the box. Where the dots are closer than this it shrinks to fit.
const MAX_WIDTH = 100
// The two pictures are about this tall for their width; the box holds either.
const BOX_HEIGHT_PER_WIDTH = 0.9

interface SwitchProps {
  length: number
  /** The part's direction, so a switch pointing left is not drawn upside down. */
  angleDeg: number
  /** Closed is on (the lit rocker); open, and anything the camera could not read, is off. */
  closed: boolean
}

/** A switch: the black box with its red rocker, lit when the switch is closed. */
export function Switch({ length, angleDeg, closed }: SwitchProps) {
  const width = Math.min(MAX_WIDTH, length)
  const height = width * BOX_HEIGHT_PER_WIDTH
  const flip = Math.abs(angleDeg) > 90
  return (
    <>
      <Leads length={length} bodyWidth={width * 0.9} />
      <g transform={`translate(${length / 2} 0) rotate(${flip ? 180 : 0})`}>
        <image
          href={closed ? switchOnUrl : switchOffUrl}
          x={-width / 2}
          y={-height / 2}
          width={width}
          height={height}
          preserveAspectRatio="xMidYMid meet"
          aria-label={closed ? 'Switch, on' : 'Switch, off'}
        />
      </g>
    </>
  )
}
