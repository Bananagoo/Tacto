import multimeterUrl from '../assets/Multimeter.png'
import { useTacto } from '../useTacto'
import { matToPoint } from './grid'

// The drawing is 608 x 842 and its red probe tip is at (340, 815). It is drawn at WIDTH_UNITS
// across, positioned so that tip lands on the fingertip: that is where the mouse is on the circuit.
const WIDTH_UNITS = 170
const SCALE = WIDTH_UNITS / 608
const HEIGHT_UNITS = 842 * SCALE
const TIP = { x: 340 * SCALE, y: 815 * SCALE }
// The screen's middle in the drawing, and how far the drawing tilts it.
const SCREEN = { x: 290 * SCALE, y: 218 * SCALE }
const SCREEN_TILT_DEG = -4

/**
 * The multimeter: the mouse as the probe. Its tip sits where the camera sees the learner's
 * fingertip, and its screen reads the current in amps and the volts across the part touched
 * (a wire has almost none). It reads the probe itself, so the fifteen position updates a
 * second re-render this and nothing else on the bench.
 */
export function Fingertip() {
  const present = useTacto((store) => store.state?.probe.present ?? false)
  const x = useTacto((store) => store.state?.probe.x ?? 0)
  const y = useTacto((store) => store.state?.probe.y ?? 0)
  const on = useTacto((store) => store.state?.probe.on ?? null)
  const current = useTacto((store) => store.state?.probe.current ?? 0)
  const buzz = useTacto((store) => store.state?.probe.buzz ?? false)
  // Volts across the touched part, from the circuit the server solved. A wire has no part.
  const partVolts = useTacto((store) => {
    const id = store.state?.probe.on
    return store.state?.circuit.parts.find((part) => part.id === id)?.voltage
  })
  if (!present) return null

  const touching = on !== null
  const volts = touching ? (partVolts ?? 0) : null
  const point = matToPoint(x, y)
  return (
    // The short linear transition joins the 15-a-second positions into one smooth movement.
    <g
      className="transition-transform duration-100 ease-linear"
      style={{ transform: `translate(${point.x}px, ${point.y}px)` }}
    >
      <image
        href={multimeterUrl}
        x={-TIP.x}
        y={-TIP.y}
        width={WIDTH_UNITS}
        height={HEIGHT_UNITS}
        aria-label="The multimeter"
      />
      {/* The readout, in amps and volts: the vibration is the current. A short says so in words. */}
      <g
        transform={`translate(${-TIP.x + SCREEN.x} ${-TIP.y + SCREEN.y}) rotate(${SCREEN_TILT_DEG})`}
        textAnchor="middle"
        fontWeight={700}
        className="fill-stone-800 tabular-nums"
      >
        {buzz ? (
          <text y={8} fontSize={19}>
            SHORT
          </text>
        ) : (
          <>
            <text y={-4} fontSize={19}>
              {touching ? `${current.toFixed(2)} A` : '-- A'}
            </text>
            <text y={17} fontSize={19}>
              {volts === null ? '-- V' : `${volts.toFixed(1)} V`}
            </text>
          </>
        )}
      </g>
    </g>
  )
}
