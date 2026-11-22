import { useRef, useState, type PointerEvent, type ReactNode } from 'react'
import { useTacto } from '../useTacto'
import { BenchNotice } from './BenchNotice'
import { DotGrid } from './DotGrid'
import { matToPoint, placeKeys, VIEW_HEIGHT, VIEW_WIDTH, type Point } from './grid'
import { Multimeter } from './Multimeter'
import { PartView } from './PartView'
import { Readout } from './Readout'
import { readingAt, readingOf } from './readingAt'
import { saveScreenshot } from './screenshot'
import { Toolbar } from './Toolbar'
import { WireLine } from './WireLine'

// Vision now sends only what the camera reads off the mat (22 Nov 2026), so the bench draws
// it. Set to false to show an empty mat whatever the server sends.
const DRAW_SERVER_CIRCUIT = true

/**
 * The mat as the camera reads it, drawn straight from the latest state. Nothing here knows
 * a layout: it draws whatever parts and wires the server lists. `children` are laid over the
 * mat's corner (the camera picture). The multimeter is the pointer over the mat.
 */
export function Bench({ children }: { children?: ReactNode }) {
  const connected = useTacto((store) => store.connected)
  const serverCircuit = useTacto((store) => store.state?.circuit)
  const circuit = DRAW_SERVER_CIRCUIT ? serverCircuit : undefined
  const wires = circuit?.wires ?? []
  const wireKeys = placeKeys(wires)
  const parts = circuit?.parts ?? []
  const short = connected && circuit?.status === 'short'
  // The multimeter is the mouse's pointer: where it is on the mat, and what it reads there.
  const svgRef = useRef<SVGSVGElement>(null)
  const [probing, setProbing] = useState(false)
  const [pointer, setPointer] = useState<Point | null>(null)
  // The learner's fingertip on the paper mat, as the camera places it.
  const probe = useTacto((store) => store.state?.probe)
  const finger = connected && probe?.present ? matToPoint(probe.x, probe.y) : null
  // The multimeter on screen wins while it is picked up; otherwise the readout follows the
  // fingertip on the paper, which is also what the mouse is vibrating for.
  const reading =
    probing && pointer
      ? readingAt(pointer, circuit, wireKeys)
      : finger && probe
        ? readingOf(probe.on, circuit, wireKeys)
        : null

  const toggleProbe = () => {
    setProbing(!probing)
    setPointer(null)
  }

  const takeScreenshot = () => {
    if (svgRef.current)
      saveScreenshot(svgRef.current).catch((error: unknown) => console.error('bench:', error))
  }

  const movePointer = (event: PointerEvent<SVGSVGElement>) => {
    if (!probing) return
    const svg = svgRef.current
    const toMat = svg?.getScreenCTM()?.inverse()
    if (!svg || !toMat) return
    const spot = svg.createSVGPoint()
    spot.x = event.clientX
    spot.y = event.clientY
    const onMat = spot.matrixTransform(toMat)
    setPointer({ x: onMat.x, y: onMat.y })
  }

  return (
    <figure
      className={`relative m-0 aspect-[96/66] min-h-0 overflow-hidden rounded-3xl bg-emerald-800 lg:aspect-auto ${
        // A thick frame as well as the banner: the short must be seen from across the room.
        short ? 'ring-8 ring-orange-500 ring-inset' : 'ring-2 ring-emerald-950 ring-inset'
      }`}
    >
      <svg
        ref={svgRef}
        onPointerMove={movePointer}
        onPointerLeave={() => setPointer(null)}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        // A stale picture is dimmed while the server is away, so it is not taken for live.
        className={`absolute inset-y-0 right-0 left-40 h-full w-[calc(100%-10rem)] transition-opacity ${probing ? 'cursor-none' : ''} ${connected ? '' : 'opacity-25'}`}
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
            touched={reading?.wireKey === wireKeys[index]}
          />
        ))}
        {parts.map((part) => (
          <PartView key={part.id} part={part} />
        ))}
        {finger && (
          <circle
            cx={finger.x}
            cy={finger.y}
            r={22}
            className="fill-white/20 stroke-white"
            strokeWidth={5}
            pointerEvents="none"
            aria-label="The fingertip on the mat"
          />
        )}
        <Multimeter point={pointer} />
      </svg>
      {/* With the server's circuit hidden, a mat that is connected reads as empty. */}
      <BenchNotice
        connected={connected}
        status={circuit?.status ?? (serverCircuit ? 'empty' : undefined)}
      />
      <Readout reading={reading} />
      <Toolbar probing={probing} onToggle={toggleProbe} onScreenshot={takeScreenshot} />
      {children}
    </figure>
  )
}
