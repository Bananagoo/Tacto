// The pre-demo setup check: one button that, in a few seconds, lets automatic brightness find
// the right setting for this room and then checks the camera, the mat, the colours, the speed
// and the voice, with what to do about anything that fails. Needs `make dev` (the lab on the
// camera); the server does the work (server/tacto/setup_check.py).

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
  pass: 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300',
  warn: 'border-amber-300/40 bg-amber-300/10 text-amber-200',
  fail: 'border-rose-400/50 bg-rose-400/10 text-rose-300',
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
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-8">
      <header className="flex flex-col gap-2">
        <h1 className="m-0 text-3xl font-bold">Setup check</h1>
        <p className="m-0 text-stone-300">
          Put the mat in view with nothing on it but the starting layout, take your hands away, and
          press the button. It sets the camera's brightness for this room, then checks everything
          the demo needs. It takes about five seconds.
        </p>
      </header>

      <button
        type="button"
        onClick={() => void run()}
        disabled={running}
        className="self-start rounded-xl bg-emerald-500 px-8 py-4 text-2xl font-bold text-emerald-950 hover:bg-emerald-400 disabled:cursor-wait disabled:opacity-60"
      >
        {running ? 'Checking…' : result ? 'Check again' : 'Run the check'}
      </button>

      {error && <p className="m-0 rounded-xl bg-rose-500/15 p-4 text-rose-200">{error}</p>}

      {result && (
        <>
          <p
            role="status"
            className={`m-0 rounded-xl border-2 p-5 text-2xl font-bold ${
              !result.ok ? COLOUR.fail : warnings ? COLOUR.warn : COLOUR.pass
            }`}
          >
            {!result.ok
              ? '✗ Not ready: fix the red items below and check again.'
              : warnings
                ? `! Ready, with ${warnings} thing${warnings === 1 ? '' : 's'} to look at.`
                : '✓ Ready for the demo.'}
            <span className="ml-3 text-base font-normal opacity-70">
              ({result.seconds.toFixed(1)} s)
            </span>
          </p>
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {result.checks.map((check) => (
              <li key={check.id} className={`rounded-xl border p-4 ${COLOUR[check.status]}`}>
                <p className="m-0 flex items-baseline gap-3 text-xl font-semibold">
                  <span aria-hidden="true" className="w-5 text-center">
                    {MARK[check.status]}
                  </span>
                  {check.label}
                  <span className="text-base font-normal text-stone-300">{check.detail}</span>
                </p>
                {check.fix && <p className="m-0 mt-2 ml-8 text-stone-100">{check.fix}</p>}
              </li>
            ))}
          </ul>
          <p className="m-0 text-sm text-stone-400">
            Not checked here: the mouse (press Connect mouse in the lab and touch a lit bulb), and
            the sound (open a question with /debug/reflect and listen).
          </p>
        </>
      )}
    </main>
  )
}
