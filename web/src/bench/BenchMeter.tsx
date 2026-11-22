import multimeterUrl from '../assets/Multimeter.png'
import { METER_MODES, type MeterMode } from './meterMode'
import type { Reading } from './readingAt'

// The dial's centre and radius, as shares of the mirrored picture's width.
const DIAL = { left: 37.6, top: 55.8, radius: 19.5 }
// Where each setting is written round the dial, in degrees from straight up.
const DIAL_ANGLES: Record<MeterMode, number> = { A: -48, V: 0, Ω: 48 }

// Where the drawing's screen is, as shares of the mirrored picture (608 x 842): its centre,
// its size, and its tilt. Measured off Multimeter.png; mirrored, the screen leans clockwise.
const SCREEN = { left: 51.9, top: 25.9, width: 41, height: 15.5, tiltDeg: 7.7 }

/** The number the screen shows in a mode, sized only: the moving dashes show the direction. */
function shown(reading: Reading | null, mode: MeterMode): string {
  if (!reading) return '--'
  if (reading.short) return 'SHORT'
  if (mode === 'A') return Math.abs(reading.current).toFixed(2)
  if (mode === 'V') return Math.abs(reading.volts).toFixed(1)
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
      className="pointer-events-none absolute right-6 bottom-0 z-10 aspect-[608/842] h-[50%] translate-y-[9%]"
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
      {/* The settings written round the dial; the one it is turned to is large and red. */}
      {METER_MODES.map((setting) => {
        const radians = (DIAL_ANGLES[setting] * Math.PI) / 180
        const chosen = setting === mode
        return (
          <span
            key={setting}
            className={`absolute -translate-x-1/2 -translate-y-1/2 font-['Patrick_Hand'] leading-none transition-all duration-200 ${
              chosen
                ? 'text-[clamp(1rem,2.2vw,1.9rem)] font-bold text-red-600'
                : 'text-[clamp(0.8rem,1.5vw,1.3rem)] text-stone-200/80'
            }`}
            style={{
              left: `${DIAL.left + Math.sin(radians) * DIAL.radius * 1.32}%`,
              top: `${DIAL.top - Math.cos(radians) * DIAL.radius * 1.32 * (608 / 842)}%`,
            }}
          >
            {setting}
          </span>
        )
      })}
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
