import type { CircuitStatus } from '../contract'

interface BenchNoticeProps {
  connected: boolean
  /** Undefined until the first state message arrives. */
  status: CircuitStatus | undefined
}

function WarningSign() {
  return (
    <svg viewBox="0 0 48 48" className="h-14 w-14 shrink-0" aria-hidden="true">
      <path d="M24 4 46 42H2Z" className="fill-black" />
      <path d="M24 17v13" className="stroke-orange-400" strokeWidth={5} strokeLinecap="round" />
      <circle cx={24} cy={36} r={3} className="fill-orange-400" />
    </svg>
  )
}

/**
 * Words laid over the mat (they let the pointer through, so the multimeter still tracks) for the states the drawing cannot explain by itself: no server,
 * nothing on the mat yet, and a short circuit. A short says so in words and with a sign,
 * because colour alone does not reach the back of the room.
 */
export function BenchNotice({ connected, status }: BenchNoticeProps) {
  if (!connected) return <Quiet>Connecting to the mat…</Quiet>
  if (status === undefined) return <Quiet>Waiting for the camera…</Quiet>
  if (status === 'empty') return <Quiet>Place a component on the mat to begin</Quiet>
  if (status !== 'short') return null
  return (
    <p
      role="alert"
      className="pointer-events-none absolute inset-x-6 top-6 m-0 flex items-center justify-center gap-5 rounded-2xl bg-orange-500 px-8 py-5 text-5xl font-extrabold tracking-wide text-black uppercase"
    >
      <WarningSign />
      Short circuit
    </p>
  )
}

function Quiet({ children }: { children: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-8">
      {/* A box round the words, so they read as a message and not as part of the drawing. */}
      <p className="m-0 max-w-xl rounded-2xl border-4 border-stone-100 bg-emerald-950 px-10 py-8 text-center text-4xl font-semibold text-stone-100">
        {children}
      </p>
    </div>
  )
}
