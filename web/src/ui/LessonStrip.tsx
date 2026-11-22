import { useEffect, type CSSProperties } from 'react'
import notebookUrl from '../assets/Notebook.png'
import { useTacto } from '../useTacto'
import { Reflection } from './Reflection'
import { StatusBar } from './StatusBar'

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
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 font-['Patrick_Hand']">
        <div className="flex items-center gap-3">
          {/* Back to the opening page (Root.tsx shows it whenever the address is not #lab). */}
          <button
            type="button"
            onClick={() => {
              location.hash = ''
            }}
            title="Back to the opening page"
            className="flex cursor-pointer items-center gap-2 rounded-2xl bg-white/5 px-4 py-2 text-xl font-semibold text-stone-300 hover:bg-white/10 hover:text-white focus-visible:outline-4 focus-visible:outline-sky-300"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
              className="h-6 w-6 fill-none stroke-current"
              strokeWidth={2.2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 11.5 12 4l9 7.5" />
              <path d="M5.5 10v9.5h13V10" />
              <path d="M10 19.5v-5h4v5" />
            </svg>
            Home
          </button>
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
          <StatusBar />
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <p className="m-0 text-lg text-stone-300">
            {mode === 'tinker'
              ? 'Build freely. Touch a piece to feel its current.'
              : 'Build, feel, then explain out loud.'}
          </p>
        </div>
      </header>
    )
  return (
    <>
      {mode === 'lab' && (
        // The lesson is handwritten on a notebook page (assets/Notebook.png). On a wide screen
        // it is as tall as the mat beside it, drawn a little wider than the picture (7:10, not
        // 0.64) so the writing has room. Its type grows and shrinks with it (cqw: a share of
        // the notebook's width), so the page reads the same on the laptop and the projector.
        <section
          aria-label="Lesson"
          className="@container relative aspect-[7/10] w-full max-w-lg shrink-0 self-center lg:h-full lg:w-auto lg:max-w-none"
        >
          <img
            src={notebookUrl}
            alt=""
            aria-hidden="true"
            draggable={false}
            className="pointer-events-none absolute inset-0 h-full w-full select-none"
          />
          {/* The writable part of the page: right of the red margin, below the rings, and
              written on the ruled lines. The lines on the drawing (measured on Notebook.png)
              start 21.8% of the way down and are 6.3% of its height apart on average, which
              at its 7:10 shape is 9cqw. Every line of writing is one --line tall, and every
              gap is a whole line, so text sits on the rules all the way down. */}
          <div
            // Never scrolls: a scrolled page would lift the writing off its lines. The page
            // holds 11 lines, and what it shows is kept to that (below).
            className="absolute overflow-hidden font-['Patrick_Hand'] text-stone-800 [&_button]:font-['Space_Grotesk_Variable'] [&_input]:font-['Space_Grotesk_Variable']"
            style={
              {
                '--line': '9cqw',
                left: '21%',
                right: '9%',
                // One line above the first rule, so the first line of writing sits on it.
                top: '15.5%',
                // The rule above the Restart lab button.
                bottom: '15.2%',
                fontSize: '5.2cqw',
                lineHeight: 'var(--line)',
                // Lowers each line of writing from the middle of its band to rest on the rule
                // below it.
                paddingTop: 'calc(var(--line) * 0.22)',
              } as CSSProperties
            }
          >
            <div>
              <div role="status" aria-atomic="true">
                <p className="m-0 text-[0.85em] font-semibold text-stone-600">
                  {ready
                    ? `Step ${lesson.step_index + 1} of ${lesson.step_count}`
                    : 'Feel the current'}
                  {done && (
                    <span className="ml-3 text-emerald-700">
                      {lesson.lesson_done ? '✓ Lesson complete' : '✓ Done'}
                    </span>
                  )}
                </p>
                {/* While a question is up the step is already done, so its instruction gives
                    way to the question and the page never needs more than its 11 lines. */}
                {!(ready && lesson.reflection) && (
                  <p className="m-0 text-[1.25em] font-semibold">
                    {ready
                      ? lesson.lesson_done
                        ? 'Same battery, different paths, and a difference you can feel.'
                        : lesson.prompt
                      : connected
                        ? 'Waiting for the lesson…'
                        : 'Connecting to the lab…'}
                  </p>
                )}
              </div>
            </div>
            {ready && lesson.reflection && lesson.reflectionStatus && (
              <Reflection lesson={lesson} onSkip={continueLesson} />
            )}
            {ready && lesson.reflection && !lesson.reflectionStatus && (
              <div className="mt-[var(--line)]">
                <div role="status">
                  <p className="m-0 text-[0.75em] font-semibold tracking-wide text-emerald-700 uppercase">
                    Explain out loud
                  </p>
                  <p className="m-0 text-[1.1em] font-semibold">{lesson.reflection}</p>
                  <p className="m-0 text-[0.75em] text-stone-600">
                    Take your time, then continue. Your voice is not being recorded.
                  </p>
                </div>
                <div className="flex h-[var(--line)] items-center gap-[0.5em] whitespace-nowrap">
                  <button
                    type="button"
                    onClick={continueLesson}
                    aria-keyshortcuts="Enter"
                    className="flex h-[calc(var(--line)*0.8)] py-0 cursor-pointer items-center rounded-lg bg-emerald-700 px-[0.8em] text-[0.75em] font-semibold text-white hover:bg-emerald-800 focus-visible:outline-4 focus-visible:outline-white"
                  >
                    {lesson.step_index === lesson.step_count - 1 ? 'Finish lab' : 'Continue'}
                    <kbd className="ml-2 rounded bg-stone-900/10 px-[0.4em] py-[0.1em] text-[0.8em]">
                      Enter
                    </kbd>
                  </button>
                </div>
              </div>
            )}
          </div>
          {/* Pinned to the page's bottom-right corner, outside the writing, so it is always
              in the same place whatever the page says. */}
          <button
            type="button"
            onClick={restartLesson}
            disabled={!connected}
            aria-keyshortcuts="R"
            title="Restart at step 1 and 3 V. Put the pieces back in the starting layout."
            className="absolute cursor-pointer rounded-lg bg-stone-800 px-[0.8em] py-[0.35em] font-['Space_Grotesk_Variable'] font-semibold text-white hover:bg-stone-700 focus-visible:outline-4 focus-visible:outline-sky-600 disabled:cursor-default disabled:opacity-40"
            style={{ right: '9%', bottom: '5%', fontSize: 'clamp(11px, 4.2cqw, 24px)' }}
          >
            Restart lab{' '}
            <kbd className="ml-2 rounded bg-white/20 px-[0.4em] py-[0.1em] text-[0.8em]">R</kbd>
          </button>
        </section>
      )}
    </>
  )
}
