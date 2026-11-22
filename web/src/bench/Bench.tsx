import { useRef, useState, type PointerEvent, type ReactNode } from 'react'
import { useTacto } from '../useTacto'
import { BenchNotice } from './BenchNotice'
import { DotGrid } from './DotGrid'
import { placeKeys, VIEW_HEIGHT, VIEW_WIDTH, type Point } from './grid'
import { MARKER_COLORS, MARKER_WIDTH, strokePath, type Stroke } from './markers'
import { Multimeter } from './Multimeter'
import { PartView } from './PartView'
import { Readout } from './Readout'
import { readingAt } from './readingAt'
import { saveScreenshot } from './screenshot'
import { Toolbar, type Tool } from './Toolbar'
import { WireLine } from './WireLine'

// The server still sends the printed lesson layout (a battery, a bulb, wire stubs) whatever the
// camera sees, because vision does not detect parts yet. Nothing is drawn from it, so the learner
// sees an empty mat. TODO(front end owner): set this to true once vision sends only what it
// detected; the bench then draws it with no other change.
const DRAW_SERVER_CIRCUIT = false

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
  const [tool, setTool] = useState<Tool>('none')
  const probing = tool === 'multimeter'
  const [pointer, setPointer] = useState<Point | null>(null)
  const reading = probing && pointer ? readingAt(pointer, circuit, wireKeys) : null
  // The marker: lines drawn over the mat for fun. They never reach the server or the solver.
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [markerColor, setMarkerColor] = useState<string>(MARKER_COLORS[0].value)
  const inking = useRef(false)

  // Clicking the tool in hand puts it down; clicking another swaps to it.
  const pickTool = (next: Tool) => {
    setTool(tool === next ? 'none' : next)
    setPointer(null)
  }

  const takeScreenshot = () => {
    if (svgRef.current)
      saveScreenshot(svgRef.current).catch((error: unknown) => console.error('bench:', error))
  }

  const spotOnMat = (event: PointerEvent<SVGSVGElement>): Point | null => {
    const svg = svgRef.current
    const toMat = svg?.getScreenCTM()?.inverse()
    if (!svg || !toMat) return null
    const spot = svg.createSVGPoint()
    spot.x = event.clientX
    spot.y = event.clientY
    const onMat = spot.matrixTransform(toMat)
    return { x: onMat.x, y: onMat.y }
  }

  const startInk = (event: PointerEvent<SVGSVGElement>) => {
    const spot = tool === 'marker' ? spotOnMat(event) : null
    if (!spot) return
    event.currentTarget.setPointerCapture(event.pointerId)
    inking.current = true
    setStrokes((all) => [...all, { color: markerColor, points: [spot] }])
  }

  const movePointer = (event: PointerEvent<SVGSVGElement>) => {
    const spot = spotOnMat(event)
    if (!spot) return
    if (probing) setPointer(spot)
    else if (tool === 'marker' && inking.current)
      setStrokes((all) => {
        const last = all[all.length - 1]
        return last ? [...all.slice(0, -1), { ...last, points: [...last.points, spot] }] : all
      })
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
        onPointerDown={startInk}
        onPointerMove={movePointer}
        onPointerUp={() => (inking.current = false)}
        onPointerCancel={() => (inking.current = false)}
        onPointerLeave={() => setPointer(null)}
        style={{ touchAction: tool === 'marker' ? 'none' : undefined }}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        // A stale picture is dimmed while the server is away, so it is not taken for live.
        className={`absolute inset-y-0 right-0 left-40 h-full w-[calc(100%-10rem)] transition-opacity ${probing ? 'cursor-none' : tool === 'marker' ? 'cursor-crosshair' : ''} ${connected ? '' : 'opacity-25'}`}
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
        {strokes.map((stroke, index) => (
          <path
            key={index}
            d={strokePath(stroke.points)}
            fill="none"
            stroke={stroke.color}
            strokeWidth={MARKER_WIDTH}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
        <Multimeter point={pointer} />
      </svg>
      {/* With the server's circuit hidden, a mat that is connected reads as empty. */}
      <BenchNotice
        connected={connected}
        status={circuit?.status ?? (serverCircuit ? 'empty' : undefined)}
      />
      <Readout reading={reading} />
      <Toolbar
        tool={tool}
        onPick={pickTool}
        markerColor={markerColor}
        onMarkerColor={setMarkerColor}
        onClearMarker={() => setStrokes([])}
        onScreenshot={takeScreenshot}
      />
      {children}
    </figure>
  )
}
