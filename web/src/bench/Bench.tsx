import type { ReactNode } from 'react'
import { useTacto } from '../useTacto'
import { BenchNotice } from './BenchNotice'
import { DotGrid } from './DotGrid'
import { Fingertip } from './Fingertip'
import { placeKeys, VIEW_HEIGHT, VIEW_WIDTH } from './grid'
import { PartView } from './PartView'
import { WireLine } from './WireLine'

// The server still sends the printed lesson layout (a battery, a bulb, wire stubs) whatever the
// camera sees, because vision does not detect parts yet. Nothing is drawn from it, so the learner
// sees an empty mat. TODO(front end owner): set this to true once vision sends only what it
// detected; the bench then draws it with no other change.
const DRAW_SERVER_CIRCUIT = false

/**
 * The mat as the camera reads it, drawn straight from the latest state. Nothing here knows
 * a layout: it draws whatever parts and wires the server lists. `children` are laid over the
 * mat's corner (the camera picture), so they take no room from the tutor beside it.
 */
export function Bench({ children }: { children?: ReactNode }) {
  const connected = useTacto((store) => store.connected)
  const serverCircuit = useTacto((store) => store.state?.circuit)
  const circuit = DRAW_SERVER_CIRCUIT ? serverCircuit : undefined
  const wires = circuit?.wires ?? []
  const wireKeys = placeKeys(wires)
  const parts = circuit?.parts ?? []
  const short = connected && circuit?.status === 'short'
  // The wire under the fingertip, as the same place key the wires are drawn under. The server
  // names it "wire:c,r-c,r" (probe.on), and null for a part or nothing.
  const touchedWire = useTacto((store) => {
    const on = store.state?.probe.on
    return on?.startsWith('wire:') ? on.slice('wire:'.length) : null
  })

  return (
    <figure
      className={`relative m-0 aspect-[96/66] min-h-0 overflow-hidden rounded-3xl bg-emerald-800 lg:aspect-auto ${
        // A thick frame as well as the banner: the short must be seen from across the room.
        short ? 'ring-8 ring-orange-500 ring-inset' : 'ring-2 ring-emerald-950 ring-inset'
      }`}
    >
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        // A stale picture is dimmed while the server is away, so it is not taken for live.
        className={`absolute inset-0 h-full w-full transition-opacity ${connected ? '' : 'opacity-25'}`}
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
            current={wire.current}
            overloaded={wire.overloaded}
            touched={wireKeys[index] === touchedWire}
          />
        ))}
        {parts.map((part) => (
          <PartView key={part.id} part={part} />
        ))}
        <Fingertip />
      </svg>
      {/* With the server's circuit hidden, a mat that is connected reads as empty. */}
      <BenchNotice
        connected={connected}
        status={circuit?.status ?? (serverCircuit ? 'empty' : undefined)}
      />
      {children}
    </figure>
  )
}
