import multimeterUrl from '../assets/Multimeter.png'
import { METER_MODES, type MeterMode } from './meterMode'
import type { Reading } from './readingAt'

// Where the drawing's screen is, as shares of the mirrored picture (608 x 842): its centre,
// its size, and its tilt. Measured off Multimeter.png; mirrored, the screen leans clockwise.
const SCREEN = { left: 51.9, top: 25.9, width: 41, height: 15.5, tiltDeg: 7.7 }
// The drawn dial's grey face: its centre and radius, as shares of the mirrored picture's
// width (radius) and of its width and height (centre). Measured off Multimeter.png.
const DIAL = { left: 41.5, top: 55.8, radius: 15.3 }
// Where each setting is written on the dial, in degrees from straight up; the pointer turns to it.
const DIAL_ANGLES: Record<MeterMode, number> = { A: -50, V: 0, Ω: 50 }
// The face's grey, sampled from the drawing, so the new dial covers the drawn one invisibly.
const FACE = '#b0b5ae'

/** The number the screen shows in a mode, sized only: the moving dashes show the direction. */
function shown(reading: Reading | null, mode: MeterMode): string {
  if (!reading) return '--'
  if (reading.short) return 'SHORT'
  if (mode === 'A') return Math.abs(reading.current).toFixed(2)
  if (mode === 'V') return Math.abs(reading.volts).toFixed(1)
  if (reading.ohms === 'OL') return 'OL'
  return reading.ohms != null ? reading.ohms.toFixed(0) : '--'
}

/**
 * The multimeter, standing large in the bench's corner while it is picked up. What the probe reads (the
 * mouse pointer over the mat, or else the fingertip on the paper) shows on its own screen, in
 * the unit its dial is set to. Every number is the server's.
 */
export function BenchMeter({
  reading,
  mode,
  onTurn,
}: {
  reading: Reading | null
  mode: MeterMode
  /** Turn the dial one setting on: a click on the dial (the thumb wheel is handled by Bench). */
  onTurn: () => void
}) {
  const value = shown(reading, mode)
  return (
    <div
      role="status"
      aria-label={`Multimeter: ${value} ${mode}`}
      // Standing in the bottom-right corner, its leads running off the bottom of the bench.
      className="pointer-events-none absolute right-6 bottom-0 z-10 aspect-[608/842] h-[50%] translate-y-[9%] [container-type:size]"
    >
      <img src={multimeterUrl} alt="" className="h-full w-full -scale-x-100 drop-shadow-xl" />
      <div
        className="absolute flex items-baseline justify-center gap-[5%] px-[8%] pt-[3%] font-bold text-stone-800 tabular-nums [container-type:size]"
        style={{
          left: `${SCREEN.left - SCREEN.width / 2}%`,
          top: `${SCREEN.top - SCREEN.height / 2}%`,
          width: `${SCREEN.width}%`,
          height: `${SCREEN.height}%`,
          transform: `rotate(${SCREEN.tiltDeg}deg)`,
        }}
      >
        <span className={value === 'SHORT' ? 'text-[36cqh]' : 'text-[50cqh] leading-none'}>
          {value}
        </span>
        {value !== 'SHORT' && <span className="text-[30cqh] leading-none">{mode}</span>}
      </div>
      {/* The dial, drawn over the picture's: small A, V and Ω round its face, and a pointer
          that turns to the one chosen. */}
      <svg
        viewBox="-100 -100 200 200"
        aria-hidden="true"
        className="absolute -translate-x-1/2 -translate-y-1/2"
        style={{
          left: `${DIAL.left}%`,
          top: `${DIAL.top}%`,
          width: `${DIAL.radius * 2}%`,
          aspectRatio: '1',
        }}
      >
        <circle r={97} fill={FACE} />
        {METER_MODES.map((setting) => {
          const radians = (DIAL_ANGLES[setting] * Math.PI) / 180
          return (
            <text
              key={setting}
              x={Math.sin(radians) * 72}
              y={-Math.cos(radians) * 72}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={setting === mode ? 34 : 28}
              fontWeight={setting === mode ? 800 : 600}
              fill={setting === mode ? '#dc2626' : '#44403c'}
            >
              {setting}
            </text>
          )
        })}
        <g
          className="transition-transform duration-300 ease-out motion-reduce:transition-none"
          style={{ transform: `rotate(${DIAL_ANGLES[mode]}deg)` }}
        >
          <rect x={-9} y={-50} width={18} height={100} rx={9} fill="#2f312d" />
          <circle cy={-38} r={6} fill="#dc2626" />
        </g>
      </svg>
      <button
        type="button"
        onClick={onTurn}
        title="Turn the dial (or use the thumb wheel)"
        aria-label={`Dial set to ${mode === 'A' ? 'amps' : mode === 'V' ? 'volts' : 'ohms'}: turn it`}
        className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-full focus-visible:outline-4 focus-visible:outline-yellow-300"
        style={{
          left: `${DIAL.left}%`,
          top: `${DIAL.top}%`,
          width: `${DIAL.radius * 2}%`,
          aspectRatio: '1',
        }}
      />
    </div>
  )
}
