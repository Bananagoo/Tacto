import { useRef, type FormEvent } from 'react'
import type { Lesson } from '../contract'
import { useTacto } from '../useTacto'

const HEADING = {
  asking: 'Explain it',
  listening: 'Listening…',
  thinking: 'Thinking…',
  resolved: '✓ That is it',
  exit: 'Here is the idea. Now try it on the mat',
} as const

/**
 * An adaptive reflection: the lab asks, the learner answers, and the lab confirms, asks a
 * narrower question, or states the idea and asks for an action on the mat. Everything shown
 * is the server's: the line it is saying, what it heard, and where it is in the exchange.
 * The answer is typed here for now; speech uses the same message.
 */
export function Reflection({ lesson, onSkip }: { lesson: Lesson; onSkip: () => void }) {
  const send = useTacto((store) => store.send)
  const box = useRef<HTMLInputElement>(null)
  const status = lesson.reflectionStatus ?? 'asking'
  const asking = status === 'asking'

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const text = box.current?.value.trim() ?? ''
    if (!asking || !text) return
    send({ type: 'answer_reflection', step_id: lesson.step_id, text })
  }

  return (
    <div className="mt-4 border-t border-white/15 pt-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        {/* aria-live: a new line from the lab is read out, the same question again included. */}
        <div role="status" aria-live="polite" className="min-w-0 flex-1">
          <p
            className={`m-0 text-sm font-semibold tracking-wide uppercase ${
              status === 'resolved' ? 'text-emerald-300' : 'text-sky-300'
            }`}
          >
            {HEADING[status]}
          </p>
          <p className="m-0 mt-1 text-xl font-semibold lg:text-2xl">
            {lesson.reflectionLine ?? lesson.reflection}
          </p>
          {lesson.reflectionTranscript !== null && (
            <p className="m-0 mt-2 text-lg text-stone-300">
              You said: “{lesson.reflectionTranscript || '(nothing heard)'}”
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onSkip}
          title="Move on without finishing this question"
          className="cursor-pointer rounded-xl bg-white/15 px-4 py-3 text-lg font-semibold hover:bg-white/25 focus-visible:outline-4 focus-visible:outline-sky-300"
        >
          Skip
        </button>
      </div>
      {(asking || status === 'thinking') && (
        // key: a new line from the lab starts with an empty box.
        <form
          key={`${lesson.step_id}:${lesson.reflectionLineId}`}
          onSubmit={submit}
          className="mt-3 flex flex-wrap gap-3"
        >
          <input
            ref={box}
            type="text"
            aria-label="Your answer"
            placeholder="Type your answer"
            autoComplete="off"
            maxLength={600}
            disabled={!asking}
            className="min-w-0 flex-1 rounded-xl border-2 border-white/20 bg-black/20 px-4 py-3 text-xl text-white placeholder:text-stone-400 focus-visible:outline-4 focus-visible:outline-sky-300 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!asking}
            className="cursor-pointer rounded-xl bg-sky-300 px-5 py-3 text-lg font-semibold text-sky-950 hover:bg-sky-200 focus-visible:outline-4 focus-visible:outline-white disabled:cursor-default disabled:opacity-50"
          >
            Answer
          </button>
        </form>
      )}
    </div>
  )
}
