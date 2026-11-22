import multimeterUrl from '../assets/Multimeter.png'
import { METER_MODES, type MeterMode } from './meterMode'
import type { Reading } from './readingAt'

// Where the drawing's screen is, as shares of the mirrored picture (608 x 842): its centre,
// its size, and its tilt. Measured off Multimeter.png; mirrored, the screen leans clockwise.
const SCREEN = { left: 51.9, top: 25.9, width: 41, height: 15.5, tiltDeg: 7.7 }
// The dial's centre and radius, as shares of the mirrored picture's width and height.
const DIAL = { left: 38.3, top: 55.8, radius: 19.7 }
// The three buttons drawn under the screen, one per setting (centres, percent of the
// mirrored picture); they lean with the screen.
const BUTTONS: Record<MeterMode, { left: number; top: number }> = {
  A: { left: 40.3, top: 40.2 },
  V: { left: 53.8, top: 41.5 },
  Ω: { left: 68.4, top: 43.4 },
}

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
      {/* The setting is shown on the buttons under the screen: the chosen one lit red. */}
      {METER_MODES.map((setting) => (
        <span
          key={setting}
          className={`absolute flex h-[5%] w-[12%] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-[1cqh] border-[0.5cqh] border-stone-900 font-bold leading-none transition-colors duration-200 [font-size:3.6cqh] ${
            setting === mode ? 'bg-red-600 text-white' : 'bg-stone-300 text-stone-700'
          }`}
          style={{
            left: `${BUTTONS[setting].left}%`,
            top: `${BUTTONS[setting].top}%`,
            transform: `translate(-50%, -50%) rotate(${SCREEN.tiltDeg}deg)`,
          }}
        >
          {setting}
        </span>
      ))}
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
