import type { Reading } from './readingAt'

/**
 * A tiny screen in the corner of the mat: what the multimeter reads under its tip, or, with
 * the multimeter put down, what is under the learner's fingertip on the paper. Sizes only:
 * which way the current runs is shown by the moving dashes, not by a minus sign. The
 * vibration is the current, in amps; the volts are across the part touched (a wire has about
 * none), not the wheel's battery setting, which the status bar shows.
 */
export function Readout({ reading }: { reading: Reading | null }) {
  return (
    <dl
      aria-label="Multimeter reading"
      className="pointer-events-none absolute top-4 right-4 z-10 m-0 grid grid-cols-[auto_auto] gap-x-5 rounded-lg border-[6px] border-stone-800 bg-lime-100 px-6 py-3 text-4xl font-bold text-stone-800 tabular-nums"
    >
      {reading?.short ? (
        <dd className="col-span-2 m-0 text-center">SHORT</dd>
      ) : (
        <>
          <dt>A</dt>
          <dd className="m-0 text-right">
            {reading ? Math.abs(reading.current).toFixed(2) : '--'}
          </dd>
          <dt>V</dt>
          <dd className="m-0 text-right">{reading ? Math.abs(reading.volts).toFixed(1) : '--'}</dd>
        </>
      )}
    </dl>
  )
}
