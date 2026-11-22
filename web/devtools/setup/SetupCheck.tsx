// The pre-demo setup check: one button that, in a few seconds, lets automatic brightness find
// the right setting for this room and then checks the camera, the mat, the colours, the speed
// and the voice, with what to do about anything that fails. Two live pictures show what the
// camera sees and what the reader makes of it, before, during and after the check. Needs
// `make dev` (the lab on the camera); the server does the work (server/tacto/setup_check.py).

import { useState } from 'react'

type Status = 'pass' | 'warn' | 'fail'

interface Check {
  id: string
  label: string
  status: Status
  detail: string
  fix: string
}

interface Result {
  ok: boolean
  seconds: number
  checks: Check[]
}

const MARK: Record<Status, string> = { pass: '✓', warn: '!', fail: '✗' }
const COLOUR: Record<Status, string> = {
  pass: 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200',
  warn: 'border-amber-300/40 bg-amber-300/10 text-amber-100',
  fail: 'border-rose-400/50 bg-rose-400/10 text-rose-200',
}

/** A live picture from the lab server, with a plain message when it cannot be had. */
function LiveView({ src, title, note }: { src: string; title: string; note: string }) {
  const [failed, setFailed] = useState(false)
  return (
    <figure className="m-0 flex flex-col gap-2 rounded-3xl bg-white/5 p-4">
      <figcaption className="flex items-baseline justify-between gap-3 px-1">
        <span className="font-['Patrick_Hand'] text-2xl text-stone-100">{title}</span>
        <span className="text-sm text-stone-400">{note}</span>
      </figcaption>
      <div className="flex aspect-[1169/827] items-center justify-center overflow-hidden rounded-2xl bg-black">
        {failed ? (
          <p className="m-0 p-6 text-center text-stone-400">
            No picture. Is the lab running with make dev, and the camera plugged in?
          </p>
        ) : (
          <img
            src={src}
            alt={title}
            onError={() => setFailed(true)}
            className="h-full w-full object-contain"
          />
        )}
      </div>
    </figure>
  )
}

export default function SetupCheck() {
  const [result, setResult] = useState<Result | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setRunning(true)
    setError('')
    try {
      const response = await fetch('/api/setup/check')
      if (!response.ok) throw new Error(`the server answered ${response.status}`)
      setResult((await response.json()) as Result)
    } catch (failure) {
      setResult(null)
      setError(
        `Could not reach the lab (${failure instanceof Error ? failure.message : String(failure)}). ` +
          'Is it running with make dev, and is the camera plugged in?',
      )
    } finally {
      setRunning(false)
    }
  }

  const warnings = result?.checks.filter((check) => check.status === 'warn').length ?? 0

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-6 pb-10 lg:px-8">
      <section className="flex flex-wrap items-center justify-between gap-6 rounded-3xl bg-white/5 p-6">
        <div className="flex max-w-2xl flex-col gap-2">
          <h1 className="m-0 font-['Patrick_Hand'] text-4xl text-stone-100">Setup check</h1>
          <p className="m-0 text-lg text-stone-300">
            Lay out the starting circuit, take your hands off the mat, and press the button. It sets
            the camera's brightness for this room, then checks everything the demo needs. About five
            seconds.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void run()}
          disabled={running}
          className="rounded-2xl bg-emerald-500 px-8 py-4 font-['Patrick_Hand'] text-3xl text-emerald-950 shadow-lg hover:bg-emerald-400 focus-visible:outline-4 focus-visible:outline-emerald-200 disabled:cursor-wait disabled:opacity-60"
        >
          {running ? 'Checking…' : result ? 'Check again' : 'Run the check'}
        </button>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <LiveView src="/api/setup/camera" title="What the camera sees" note="live" />
        <LiveView
          src="/api/setup/view"
          title="What the reader sees"
          note="the mat squared up, each piece labelled"
        />
      </div>

      {error && <p className="m-0 rounded-2xl bg-rose-500/15 p-4 text-lg text-rose-200">{error}</p>}

      {result && (
        <section className="flex flex-col gap-4">
          <p
            role="status"
            className={`m-0 rounded-2xl border-2 p-5 font-['Patrick_Hand'] text-3xl ${
              !result.ok ? COLOUR.fail : warnings ? COLOUR.warn : COLOUR.pass
            }`}
          >
            {!result.ok
              ? '✗ Not ready: fix the red items below and check again.'
              : warnings
                ? `! Ready, with ${warnings} thing${warnings === 1 ? '' : 's'} to look at.`
                : '✓ Ready for the demo.'}
            <span className="ml-3 font-sans text-base opacity-70">
              ({result.seconds.toFixed(1)} s)
            </span>
          </p>
          <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
            {result.checks.map((check) => (
              <li key={check.id} className={`rounded-2xl border p-4 ${COLOUR[check.status]}`}>
                <p className="m-0 flex items-baseline gap-3 text-xl font-semibold">
                  <span aria-hidden="true" className="w-5 text-center">
                    {MARK[check.status]}
                  </span>
                  {check.label}
                </p>
                <p className="m-0 mt-1 ml-8 text-stone-300">{check.detail}</p>
                {check.fix && <p className="m-0 mt-2 ml-8 text-stone-50">{check.fix}</p>}
              </li>
            ))}
          </ul>
          <p className="m-0 text-sm text-stone-400">
            Not checked here: the mouse (press Connect mouse in the lab and touch a lit bulb), and
            the sound (open a question with /debug/reflect and listen).
          </p>
        </section>
      )}
    </main>
  )
}
