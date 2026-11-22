import multimeterUrl from '../assets/Multimeter.png'
import type { Reading } from './readingAt'

/** What the meter's dial is set to: amps, volts or ohms. */
export type MeterMode = 'A' | 'V' | 'Ω'

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
 * The multimeter, set down large on the bench while it is picked up. What the probe reads (the
 * mouse pointer over the mat, or else the fingertip on the paper) shows on its own screen, in
 * the unit its dial is set to. Every number is the server's.
 */
export function BenchMeter({ reading, mode }: { reading: Reading | null; mode: MeterMode }) {
  const value = shown(reading, mode)
  return (
    <div
      role="status"
      aria-label={`Multimeter: ${value} ${mode}`}
      className="pointer-events-none absolute top-4 right-4 z-10 aspect-[608/842] h-[62%]"
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
    </div>
  )
}
