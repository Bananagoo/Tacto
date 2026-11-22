import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from 'react'
import type { Part, Wire } from '../contract'
import { useTacto } from '../useTacto'
import { BenchNotice } from './BenchNotice'
import { DotGrid } from './DotGrid'
import { matToPoint, placeKeys, VIEW_HEIGHT, VIEW_WIDTH, type Point } from './grid'
import {
  DEFAULT_ERASER_RADIUS,
  MARKER_COLORS,
  MARKER_WIDTH,
  strokePath,
  eraseFromStroke,
  type Stroke,
} from './markers'
import { BenchMeter } from './BenchMeter'
import { turnDial, type MeterMode } from './meterMode'
import { tallyWheel } from '../input/wheel'
import { PartView } from './PartView'
import { VoltageTag } from './VoltageTag'
import { readingAt, readingOf } from './readingAt'
import { saveShot } from '../gallery/shots'
import { screenshotBlob, SKIP_IN_SCREENSHOT } from './screenshot'
import { Toolbar, type Tool } from './Toolbar'
import { useLingering } from './useLingering'
import { WireLine } from './WireLine'

// Vision now sends only what the camera reads off the mat (22 Nov 2026), so the bench draws
// it. Set to false to show an empty mat whatever the server sends.
const DRAW_SERVER_CIRCUIT = true
// After the thumb wheel turns the meter's dial, the rest of that flick is ignored for this long.
const DIAL_QUIET_MS = 450

const partKey = (part: Part) => `${part.id}:${part.kind}:${part.closed}`
const wireKey = (wire: Wire) => wire.id

/**
 * The mat as the camera reads it, drawn straight from the latest state. Nothing here knows
 * a layout: it draws whatever parts and wires the server lists. `children` are laid over the
 * mat's corner (the camera picture). Picked up, the multimeter sits large on the bench and
 * reads whatever the pointer is over.
 */
export function Bench({ children }: { children?: ReactNode }) {
  const connected = useTacto((store) => store.connected)
  const serverCircuit = useTacto((store) => store.state?.circuit)
  const circuit = DRAW_SERVER_CIRCUIT ? serverCircuit : undefined
  const wires = circuit?.wires ?? []
  const wireKeys = placeKeys(wires)
  const parts = circuit?.parts ?? []
  const short = connected && circuit?.status === 'short'
  const goneParts = useLingering(parts, partKey)
  const goneWires = useLingering(wires, wireKey)
  // The multimeter is the mouse's pointer: where it is on the mat, and what it reads there.
  const svgRef = useRef<SVGSVGElement>(null)
  const [tool, setTool] = useState<Tool>('none')
  const probing = tool === 'multimeter'
  const [meterMode, setMeterMode] = useState<MeterMode>('A')
  // The thumb wheel (sideways scroll) turns the meter's dial, one setting per notch's worth.
  // The main wheel is the voltage (useVoltageWheel), which reads only the up-and-down scroll.
  useEffect(() => {
    if (!probing) return
    let remainder = 0
    let quietUntil = 0
    const onWheel = (event: WheelEvent) => {
      if (Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return
      // One setting per flick (Katie: it went too fast): after a turn, the rest of that flick
      // is ignored, and a turn takes a full notch's worth of scroll.
      if (event.timeStamp < quietUntil) {
        remainder = 0
        return
      }
      const tally = tallyWheel(remainder, event.deltaX)
      remainder = tally.remainder
      if (tally.steps === 0) return
      remainder = 0
      quietUntil = event.timeStamp + DIAL_QUIET_MS
      setMeterMode((mode) => turnDial(mode, Math.sign(tally.steps)))
    }
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => window.removeEventListener('wheel', onWheel)
  }, [probing])
  const [pointer, setPointer] = useState<Point | null>(null)
  // The learner's fingertip on the paper mat, as the camera places it.
  const probe = useTacto((store) => store.state?.probe)
  const finger = connected && probe?.present ? matToPoint(probe.x, probe.y) : null
  // The pointer over the mat is the meter's probe while it is picked up; otherwise the
  // reading follows the fingertip on the paper, which is what the mouse is vibrating for.
  const reading =
    probing && pointer
      ? readingAt(pointer, circuit, wireKeys)
      : finger && probe
        ? readingOf(probe.on, circuit, wireKeys)
        : null
  // The marker: lines drawn over the mat for fun. They never reach the server or the solver.
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [markerColor, setMarkerColor] = useState<string>(MARKER_COLORS[0].value)
  const [eraserRadius, setEraserRadius] = useState(DEFAULT_ERASER_RADIUS)
  const inking = useRef(false)

  // Clicking the tool in hand puts it down; clicking another swaps to it.
  const pickTool = (next: Tool) => {
    setTool(tool === next ? 'none' : next)
    setPointer(null)
  }

  // Keeps a dated picture of the circuit in the gallery. Resolves when it is saved.
  const takeScreenshot = async () => {
    if (!svgRef.current) return
    await saveShot(await screenshotBlob(svgRef.current))
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

  // The eraser takes out only the part of a line under it, and leaves the rest.
  const erase = (spot: Point) =>
    setStrokes((all) => {
      let changed = false
      const next = all.flatMap((stroke) => {
        const left = eraseFromStroke(stroke, spot, eraserRadius)
        if (left.length !== 1 || left[0] !== stroke) changed = true
        return left
      })
      return changed ? next : all
    })

  // Pressing with the marker starts a line, and with the eraser starts erasing.
  const startInk = (event: PointerEvent<SVGSVGElement>) => {
    if (tool !== 'marker' && tool !== 'eraser') return
    const spot = spotOnMat(event)
    if (!spot) return
    event.currentTarget.setPointerCapture(event.pointerId)
    inking.current = true
    if (tool === 'eraser') erase(spot)
    else setStrokes((all) => [...all, { color: markerColor, points: [spot] }])
  }

  const movePointer = (event: PointerEvent<SVGSVGElement>) => {
    const spot = spotOnMat(event)
    if (!spot) return
    // The multimeter and the eraser's ring both follow the pointer.
    if (probing || tool === 'eraser') setPointer(spot)
    if (!inking.current) return
    if (tool === 'eraser') erase(spot)
    else if (tool === 'marker')
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
        style={{ touchAction: tool === 'marker' || tool === 'eraser' ? 'none' : undefined }}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        // A stale picture is dimmed while the server is away, so it is not taken for live.
        className={`absolute inset-y-0 right-0 left-40 h-full w-[calc(100%-10rem)] transition-opacity ${tool === 'eraser' ? 'cursor-none' : tool === 'marker' ? 'cursor-crosshair' : ''} ${connected ? '' : 'opacity-25'}`}
        role="img"
        aria-label="The circuit on the mat"
      >
        <DotGrid />
        {/* Pieces fade in when the camera first reads them and fade out when lifted, instead
            of blinking. Only what was really read is drawn: nothing follows the hand. */}
        {goneWires.map(({ key, item: wire }) => (
          <g key={`gone-${key}`} className="piece-out">
            <WireLine
              aCol={wire.a[0]}
              aRow={wire.a[1]}
              bCol={wire.b[0]}
              bRow={wire.b[1]}
              current={0}
              overloaded={false}
              touched={false}
            />
          </g>
        ))}
        {wires.map((wire, index) => (
          <g key={wireKeys[index]} className="piece-in">
            <WireLine
              aCol={wire.a[0]}
              aRow={wire.a[1]}
              bCol={wire.b[0]}
              bRow={wire.b[1]}
              current={wire.current}
              overloaded={wire.overloaded}
              touched={reading?.wireKey === wireKeys[index]}
            />
          </g>
        ))}
        {parts
          .filter((part) => part.kind === 'battery')
          .map((battery) => (
            <VoltageTag
              key={`volts-${battery.id}`}
              battery={battery}
              volts={circuit?.source_voltage ?? 0}
            />
          ))}
        {goneParts.map(({ key, item: part }) => (
          <g key={`gone-${key}`} className="piece-out">
            <PartView part={part} />
          </g>
        ))}
        {parts.map((part) => (
          // Keyed by what the piece is as well as where: swapping the open switch for the
          // closed one is one piece leaving and another arriving.
          <g key={partKey(part)} className="piece-in">
            <PartView part={part} />
          </g>
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
        {finger && (
          <circle
            cx={finger.x}
            cy={finger.y}
            r={22}
            className="fill-white/20 stroke-white"
            strokeWidth={5}
            pointerEvents="none"
            // Glides between the server's 15 positions a second instead of jumping.
            style={{ transition: 'cx 90ms linear, cy 90ms linear' }}
            aria-label="The fingertip on the mat"
          />
        )}
        {tool === 'eraser' && pointer && (
          // A ring the size of the eraser's reach, so it is clear what it will take.
          <circle
            cx={pointer.x}
            cy={pointer.y}
            r={eraserRadius}
            className="fill-white/20 stroke-white"
            strokeWidth={4}
            pointerEvents="none"
            {...{ [SKIP_IN_SCREENSHOT]: true }}
          />
        )}
      </svg>
      {/* With the server's circuit hidden, a mat that is connected reads as empty. */}
      <BenchNotice
        connected={connected}
        status={circuit?.status ?? (serverCircuit ? 'empty' : undefined)}
      />
      {/* Readings are shown only on the meter's own screen, while it is picked up. */}
      {probing && (
        <BenchMeter
          reading={reading}
          mode={meterMode}
          onTurn={() => setMeterMode((mode) => turnDial(mode, 1))}
        />
      )}
      <Toolbar
        tool={tool}
        onPick={pickTool}
        markerColor={markerColor}
        onMarkerColor={setMarkerColor}
        onClearMarker={() => setStrokes([])}
        eraserRadius={eraserRadius}
        onEraserRadius={setEraserRadius}
        onScreenshot={takeScreenshot}
      />
      {children}
    </figure>
  )
}
