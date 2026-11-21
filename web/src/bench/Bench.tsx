import { useTacto } from '../useTacto'
import { DotGrid } from './DotGrid'
import { Fingertip } from './Fingertip'
import { placeKeys, VIEW_HEIGHT, VIEW_WIDTH } from './grid'
import { PartView } from './PartView'
import { WireLine } from './WireLine'

/**
 * The mat as the camera reads it, drawn straight from the latest state. Nothing here knows
 * a layout: it draws whatever parts and wires the server lists.
 */
export function Bench() {
  const circuit = useTacto((store) => store.state?.circuit)
  const wires = circuit?.wires ?? []
  const wireKeys = placeKeys(wires)
  const parts = circuit?.parts ?? []

  return (
    <figure className="relative m-0 aspect-[96/66] min-h-0 rounded-3xl bg-white/5 lg:aspect-auto">
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        className="absolute inset-0 h-full w-full"
        role="img"
        aria-label="The circuit on the mat"
      >
        <DotGrid />
        {wires.map((wire, index) => (
          <WireLine
            key={wireKeys[index]}
            aCol={wire.a[0]}
            aRow={wire.a[1]}
            bCol={wire.b[0]}
            bRow={wire.b[1]}
          />
        ))}
        {parts.map((part) => (
          <PartView key={part.id} part={part} />
        ))}
        <Fingertip />
      </svg>
    </figure>
  )
}
