import type { Reading } from './readingAt'

/**
 * A tiny screen in the corner of the mat: what the multimeter reads under its tip. The
 * vibration is the current, in amps; the volts are across the part touched (a wire has about
 * none), not the wheel's battery setting, which the status bar shows.
 */
export function Readout({ reading }: { reading: Reading | null }) {
  return (
    <dl
      aria-label="Multimeter reading"
      className="pointer-events-none absolute top-4 right-4 z-10 m-0 grid grid-cols-[auto_auto] gap-x-3 rounded-lg border-4 border-stone-800 bg-lime-100/90 px-4 py-2 text-2xl font-bold text-stone-800 tabular-nums"
    >
      {reading?.short ? (
        <dd className="col-span-2 m-0 text-center">SHORT</dd>
      ) : (
        <>
          <dt>A</dt>
          <dd className="m-0 text-right">{reading ? reading.current.toFixed(2) : '--'}</dd>
          <dt>V</dt>
          <dd className="m-0 text-right">{reading ? reading.volts.toFixed(1) : '--'}</dd>
        </>
      )}
    </dl>
  )
}
