import { useEffect } from 'react'
import notebookUrl from '../assets/Notebook.png'
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
/** The Tinker / Lab switch: a thin bar along the top. It also owns the lesson's keys. */
export function ModeBar() {
  return <LessonStrip part="bar" />
}

/**
 * The lesson itself, in Lab mode: the prompt, and the reflection when one is up. It stands
 * in a column beside the mat on a wide screen, so the mat keeps its full height however
 * much the lesson has to say. Nothing in Tinker mode.
 */
export function LessonPanel() {
  return <LessonStrip part="panel" />
}

function LessonStrip({ part }: { part: 'bar' | 'panel' }) {
  const connected = useTacto((store) => store.connected)
  const mode = useTacto((store) => store.state?.mode ?? 'tinker')
  const send = useTacto((store) => store.send)
  const lesson = useTacto((store) => store.state?.lesson)

  useEffect(() => {
    // Once, by the bar: the panel comes and goes with the mode.
    if (part !== 'bar') return
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
  }, [part])

  const ready = connected && lesson && lesson.step_count > 0
  const done = ready && lesson.step_done

  if (part === 'panel' && mode !== 'lab') return null
  if (part === 'bar')
    return (
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
    )
  return (
    <>
      {mode === 'lab' && (
        // The lesson is written on a notebook page (assets/Notebook.png). The picture keeps its
        // shape: on a wide screen it is as tall as the mat beside it, and its type grows and
        // shrinks with it (cqw: a share of the notebook's width), so the page reads the same
        // on the laptop and on the projector.
        <section
          aria-label="Lesson"
          className="@container relative aspect-[1010/1517] w-full max-w-md shrink-0 self-center lg:h-full lg:w-auto lg:max-w-none"
        >
          <img
            src={notebookUrl}
            alt=""
            aria-hidden="true"
            draggable={false}
            className="pointer-events-none absolute inset-0 h-full w-full select-none"
          />
          {/* The writable part of the page: right of the red margin, below the rings. */}
          <div
            className="absolute overflow-y-auto text-stone-800"
            style={{
              left: '23%',
              right: '13%',
              top: '12%',
              bottom: '10%',
              fontSize: 'clamp(11px, 4.4cqw, 26px)',
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div role="status" aria-atomic="true" className="min-w-0 flex-1 basis-full">
                <p className="m-0 mb-2 text-[0.85em] font-semibold text-stone-600">
                  {ready
                    ? `Step ${lesson.step_index + 1} of ${lesson.step_count}`
                    : 'Feel the current'}
                  {done && (
                    <span className="ml-3 text-emerald-700">
                      {lesson.lesson_done ? '✓ Lesson complete' : '✓ Done'}
                    </span>
                  )}
                </p>
                <p className="m-0 text-[1.3em] leading-snug font-semibold">
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
                className="cursor-pointer rounded-lg bg-stone-900/10 px-[0.7em] py-[0.35em] text-[0.85em] font-semibold hover:bg-stone-900/20 focus-visible:outline-4 focus-visible:outline-sky-600 disabled:cursor-default disabled:opacity-40"
              >
                Restart{' '}
                <kbd className="ml-2 rounded bg-stone-900/10 px-[0.4em] py-[0.1em] text-[0.8em]">
                  R
                </kbd>
              </button>
            </div>
            {ready && lesson.reflection && lesson.reflectionStatus && (
              <Reflection lesson={lesson} onSkip={continueLesson} />
            )}
            {ready && lesson.reflection && !lesson.reflectionStatus && (
              <div className="mt-[0.8em] flex flex-wrap items-center justify-between gap-[0.6em] border-t border-stone-500/40 pt-[0.8em]">
                <div role="status" className="min-w-0 flex-1 basis-full">
                  <p className="m-0 text-[0.75em] font-semibold tracking-wide text-emerald-700 uppercase">
                    Explain out loud
                  </p>
                  <p className="m-0 mt-1 text-[1.1em] font-semibold">{lesson.reflection}</p>
                  <p className="m-0 mt-1 text-[0.75em] text-stone-600">
                    Take your time, then continue. Your voice is not being recorded.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={continueLesson}
                  aria-keyshortcuts="Enter"
                  className="cursor-pointer rounded-lg bg-emerald-700 px-[0.8em] py-[0.4em] text-[0.9em] font-semibold text-white hover:bg-emerald-800 focus-visible:outline-4 focus-visible:outline-white"
                >
                  {lesson.step_index === lesson.step_count - 1 ? 'Finish lab' : 'Continue'}
                  <kbd className="ml-2 rounded bg-stone-900/10 px-[0.4em] py-[0.1em] text-[0.8em]">
                    Enter
                  </kbd>
                </button>
              </div>
            )}
          </div>
        </section>
      )}
    </>
  )
}
