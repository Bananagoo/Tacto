import { Leads } from './Leads'

const RADIUS = 36
// The cross of the lamp symbol reaches the circle at 45 degrees.
const CROSS = RADIUS * Math.SQRT1_2
// How far the halo spreads at full brightness, as a multiple of the bulb's radius.
const HALO_REACH = 1.5

interface BulbProps {
  length: number
  /** 0 (off) to 1 (full), from the server. */
  brightness: number
}

/**
 * A lamp. Brightness shows as light, not hue: the fill and the halo fade in and the halo
 * grows, so a dim bulb, a bright one and a dark one read differently in greyscale too.
 */
export function Bulb({ length, brightness }: BulbProps) {
  const level = Number.isFinite(brightness) ? Math.min(1, Math.max(0, brightness)) : 0
  return (
    <>
      <Leads length={length} bodyWidth={RADIUS * 2} />
      <g transform={`translate(${length / 2} 0)`}>
        {/* The transitions carry the glow from one state message to the next without a jump. */}
        <circle
          r={RADIUS}
          className="fill-amber-300 stroke-none transition-[opacity,transform] duration-300 ease-out"
          style={{ opacity: 0.4 * level, transform: `scale(${1 + HALO_REACH * level})` }}
        />
        {/* An opaque disc, so the dots and wires behind do not show through an unlit bulb. */}
        <circle r={RADIUS} className="fill-[#0f1115] stroke-none" />
        <circle
          r={RADIUS}
          className="fill-amber-200 stroke-none transition-opacity duration-300 ease-out"
          style={{ opacity: level }}
        />
        <circle r={RADIUS} />
        {/* On a lit bulb the pale strokes would vanish into the fill, so the cross goes dark. */}
        <path
          d={`M ${-CROSS} ${-CROSS} L ${CROSS} ${CROSS} M ${-CROSS} ${CROSS} L ${CROSS} ${-CROSS}`}
          className={level > 0.5 ? 'stroke-stone-900' : undefined}
          strokeWidth={4}
        />
      </g>
    </>
  )
}
