import { useEffect } from 'react'
import { useTacto } from '../useTacto'
import { Reflection } from './Reflection'

function restartLesson() {
  const { connected, state, send } = useTacto.getState()
  if (connected && state?.mode === 'lab') send({ type: 'restart_lesson' })
}

/** Move on from a reflection. Does nothing unless one is showing. */
function continueLesson() {
  const { connected, state, send } = useTacto.getState()
  if (connected && state?.mode === 'lab' && state.lesson.reflection)
    send({ type: 'continue_lesson', step_id: state.lesson.step_id })
}

/** One instruction beside the bench; completion stays visible while the learner feels it. */
export function LessonStrip() {
  const connected = useTacto((store) => store.connected)
  const mode = useTacto((store) => store.state?.mode ?? 'tinker')
  const send = useTacto((store) => store.send)
  const lesson = useTacto((store) => store.state?.lesson)
  const volts = useTacto((store) => store.state?.circuit.source_voltage)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (useTacto.getState().state?.mode !== 'lab') return
      // R restarts; Enter moves on from a reflection, so nobody has to find the button
      // with their hands on the mat and the mouse.
      const key = event.key.toLowerCase()
      if (
        (key !== 'r' && key !== 'enter') ||
        event.repeat ||
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey ||
        event.defaultPrevented
      )
        return
      const target = event.target
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          // Enter on a focused button already presses that button.
          target.closest(
            key === 'enter'
              ? 'input, textarea, select, button, a, [role="textbox"]'
              : 'input, textarea, select, [role="textbox"]',
          ))
      )
        return
      event.preventDefault()
      if (key === 'r') restartLesson()
      // In an adaptive reflection Enter belongs to the answer box; moving on is the Skip button.
      else if (!useTacto.getState().state?.lesson.reflectionStatus) continueLesson()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const ready = connected && lesson && lesson.step_count > 0
  const done = ready && lesson.step_done

  return (
    <>
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        <div
          role="group"
          aria-label="Learning mode"
          className="flex gap-1 rounded-2xl bg-white/5 p-1"
        >
          {(['tinker', 'lab'] as const).map((choice) => (
            <button
              key={choice}
              type="button"
              aria-pressed={mode === choice}
              disabled={!connected}
              onClick={() => {
                if (mode !== choice) send({ type: 'set_mode', mode: choice })
              }}
              title={
                choice === 'lab'
                  ? 'Start a guided lab at step 1 and 3 V'
                  : 'Explore freely with your current circuit'
              }
              className={`cursor-pointer rounded-xl px-6 py-2 text-xl font-semibold focus-visible:outline-4 focus-visible:outline-sky-300 disabled:opacity-40 ${mode === choice ? 'bg-white/15 text-white' : 'text-stone-400 hover:text-white'}`}
            >
              {choice === 'tinker' ? 'Tinker' : 'Lab'}
            </button>
          ))}
        </div>
        <p className="m-0 text-lg text-stone-300">
          {mode === 'tinker'
            ? 'Build freely. Touch a piece to feel its current.'
            : 'Build, feel, then explain out loud.'}
        </p>
      </header>
      {mode === 'lab' && (
        <section
          aria-label="Lesson"
          className={`shrink-0 rounded-3xl border-2 px-6 py-4 transition-colors lg:px-8 ${
            done ? 'border-emerald-400/60 bg-emerald-400/10' : 'border-white/10 bg-white/5'
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div role="status" aria-atomic="true" className="min-w-0 flex-1">
              <p className="m-0 mb-2 text-lg font-semibold text-stone-300">
                {ready
                  ? `Step ${lesson.step_index + 1} of ${lesson.step_count}`
                  : 'Feel the current'}
                {done && (
                  <span className="ml-4 text-emerald-300">
                    {lesson.lesson_done ? '✓ Lesson complete' : '✓ Done'}
                  </span>
                )}
              </p>
              <p className="m-0 text-2xl leading-snug font-semibold xl:text-3xl">
                {ready
                  ? lesson.lesson_done
                    ? 'Same two bulbs, different connections—and a difference you can feel.'
                    : lesson.prompt
                  : connected
                    ? 'Waiting for the lesson…'
                    : 'Connecting to the lab…'}
              </p>
            </div>
            <button
              type="button"
              onClick={restartLesson}
              disabled={!connected}
              aria-keyshortcuts="R"
              title="Restart at step 1 and 3 V. Put the pieces back in the starting layout."
              className="cursor-pointer rounded-xl bg-white/15 px-4 py-3 text-lg font-semibold hover:bg-white/25 focus-visible:outline-4 focus-visible:outline-sky-300 disabled:cursor-default disabled:opacity-40"
            >
              Restart <kbd className="ml-2 rounded bg-black/20 px-2 py-1 text-sm">R</kbd>
            </button>
          </div>
          {ready && lesson.reflection && lesson.reflectionStatus && (
            <Reflection lesson={lesson} onSkip={continueLesson} />
          )}
          {ready && lesson.reflection && !lesson.reflectionStatus && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-4 border-t border-white/15 pt-4">
              <div role="status" className="min-w-0 flex-1">
                <p className="m-0 text-sm font-semibold tracking-wide text-emerald-300 uppercase">
                  Explain out loud
                </p>
                <p className="m-0 mt-1 text-xl font-semibold lg:text-2xl">{lesson.reflection}</p>
                <p className="m-0 mt-1 text-sm text-stone-300">
                  Take your time, then continue. Your voice is not being recorded.
                </p>
              </div>
              <button
                type="button"
                onClick={continueLesson}
                aria-keyshortcuts="Enter"
                className="cursor-pointer rounded-xl bg-emerald-300 px-5 py-3 text-lg font-semibold text-emerald-950 hover:bg-emerald-200 focus-visible:outline-4 focus-visible:outline-white"
              >
                {lesson.step_index === lesson.step_count - 1 ? 'Finish lab' : 'Continue'}
                <kbd className="ml-2 rounded bg-black/20 px-2 py-1 text-sm">Enter</kbd>
              </button>
            </div>
          )}
          <p className="m-0 mt-3 text-lg text-stone-300">
            {connected && volts !== undefined && (
              <span className="font-semibold">{volts.toFixed(1)} V · </span>
            )}
            Wheel controls voltage · Mouse pulse represents current
          </p>
        </section>
      )}
    </>
  )
}
