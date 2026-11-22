import type { Reading } from './readingAt'

/**
 * A tiny screen in the corner of the mat: what the multimeter reads under its tip, or, with
 * the multimeter put down, what is under the learner's fingertip on the paper. Sizes only:
 * which way the current runs is shown by the moving dashes, not by a minus sign. The
 * vibration is the current, in amps; the volts are across the part touched (a wire has about
 * none), not the wheel's battery setting, which the status bar shows. The ohms show for a
 * bulb or a resistor, so the three numbers can be checked against V = I x R.
 */
export function Readout({ reading }: { reading: Reading | null }) {
  const short = reading?.short === true
  return (
    // Always the size of its widest reading, so it does not jump as readings come and go: each
    // number has room for "0.00", and a short is written over the two lines, not instead of them.
    <dl
      aria-label="Multimeter reading"
      className="pointer-events-none absolute top-4 right-4 z-10 m-0 grid grid-cols-[auto_auto] gap-x-5 rounded-lg border-[6px] border-stone-800 bg-lime-100 px-6 py-3 text-4xl font-bold text-stone-800 tabular-nums"
    >
      <dt className={short ? 'invisible' : ''}>A</dt>
      <dd className={`m-0 min-w-[4ch] text-right ${short ? 'invisible' : ''}`}>
        {reading ? Math.abs(reading.current).toFixed(2) : '--'}
      </dd>
      <dt className={short ? 'invisible' : ''}>V</dt>
      <dd className={`m-0 min-w-[4ch] text-right ${short ? 'invisible' : ''}`}>
        {reading ? Math.abs(reading.volts).toFixed(1) : '--'}
      </dd>
      <dt className={short ? 'invisible' : ''}>Ω</dt>
      <dd className={`m-0 min-w-[4ch] text-right ${short ? 'invisible' : ''}`}>
        {reading?.ohms != null ? reading.ohms.toFixed(0) : '--'}
      </dd>
      {short && <dd className="absolute inset-0 m-0 flex items-center justify-center">SHORT</dd>}
    </dl>
  )
}
