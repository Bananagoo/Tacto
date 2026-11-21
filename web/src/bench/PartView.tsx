import { memo } from 'react'
import type { Part } from '../contract'
import { dotToPoint, spanBetween } from './grid'
import { Battery } from './parts/Battery'
import { Bulb } from './parts/Bulb'
import { Resistor } from './parts/Resistor'
import { Switch } from './parts/Switch'

function Symbol({ part, length, angleDeg }: { part: Part; length: number; angleDeg: number }) {
  switch (part.kind) {
    case 'battery':
      return <Battery length={length} />
    case 'bulb':
      return <Bulb length={length} angleDeg={angleDeg} brightness={part.brightness} />
    case 'resistor':
      return <Resistor length={length} />
    case 'switch':
      // `closed` is null for anything the camera could not read; an unknown switch is open.
      return <Switch length={length} closed={part.closed === true} />
  }
}

// Every state message carries new part objects, so compare what is drawn, not identity.
function sameDrawing({ part: before }: { part: Part }, { part: after }: { part: Part }): boolean {
  return (
    before.kind === after.kind &&
    before.a[0] === after.a[0] &&
    before.a[1] === after.a[1] &&
    before.b[0] === after.b[0] &&
    before.b[1] === after.b[1] &&
    before.closed === after.closed &&
    before.brightness === after.brightness
  )
}

/**
 * Places a part's symbol between its two dots, at any angle. Each symbol draws itself along
 * the x axis from 0 to `length`; the turn and the move happen here, once.
 */
export const PartView = memo(function PartView({ part }: { part: Part }) {
  const a = dotToPoint(part.a)
  const { length, angleDeg } = spanBetween(a, dotToPoint(part.b))
  return (
    <g
      transform={`translate(${a.x} ${a.y}) rotate(${angleDeg})`}
      className="fill-none stroke-stone-100"
      strokeWidth={6}
      strokeLinecap="round"
    >
      <Symbol part={part} length={length} angleDeg={angleDeg} />
    </g>
  )
}, sameDrawing)
