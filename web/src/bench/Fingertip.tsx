import { useTacto } from '../useTacto'
import { matToPoint } from './grid'

/**
 * Where the camera sees the learner's fingertip. It reads the probe itself, so the fifteen
 * position updates a second re-render this ring and nothing else on the bench.
 */
export function Fingertip() {
  const present = useTacto((store) => store.state?.probe.present ?? false)
  const x = useTacto((store) => store.state?.probe.x ?? 0)
  const y = useTacto((store) => store.state?.probe.y ?? 0)
  const touching = useTacto((store) => store.state?.probe.on != null)
  const current = useTacto((store) => store.state?.probe.current ?? 0)
  const buzz = useTacto((store) => store.state?.probe.buzz ?? false)
  if (!present) return null

  const point = matToPoint(x, y)
  return (
    // The short linear transition joins the 15-a-second positions into one smooth movement.
    <g
      className="fill-none transition-transform duration-100 ease-linear"
      style={{ transform: `translate(${point.x}px, ${point.y}px)` }}
    >
      {/* A dark ring under the white one keeps the fingertip visible over a lit bulb. */}
      <circle r={26} className="stroke-black/70" strokeWidth={14} />
      <circle r={26} className="stroke-white" strokeWidth={6} />
      {touching && <circle r={8} className="fill-white" />}
      {/* What the mouse is feeling, in amps: the vibration is the current. A short says so in
          words, because the rate alone does not. Dark outline so it reads over any wire. */}
      {touching && (
        <text
          x={40}
          y={-34}
          fontSize={34}
          fontWeight={700}
          className="fill-white stroke-black/80"
          strokeWidth={8}
          paintOrder="stroke"
        >
          {buzz ? 'Short! buzz' : `${current.toFixed(2)} A`}
        </text>
      )}
    </g>
  )
}
