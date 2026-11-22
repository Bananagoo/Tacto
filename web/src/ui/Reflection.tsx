import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Lesson } from '../contract'
import { useTacto } from '../useTacto'
import { useAnswerMic, type MicState } from '../voice/useAnswerMic'

const HEADING = {
  asking: 'Explain it',
  listening: 'Listening…',
  thinking: 'Thinking…',
  resolved: '✓ That is it',
  exit: 'Here is the idea. Now try it on the mat',
} as const

const MIC_WORDS: Record<MicState, string> = {
  off: 'Hold Space to talk, or type below.',
  starting: 'Opening the microphone…',
  listening: 'Go ahead, I am listening.',
  hearing: 'I can hear you…',
  sending: 'Working out what you said…',
  failed: '',
}

const VOICE_CHOICE = 'tacto-answer-by-voice'

function choseVoice(): boolean {
  try {
    return sessionStorage.getItem(VOICE_CHOICE) === 'yes'
  } catch {
    return false
  }
}

/** True where Space is typing a space: push-to-talk leaves those alone. */
function isTextEntry(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      target.closest('input, textarea, select, [role="textbox"]') !== null)
  )
}

/**
 * An adaptive reflection: the lab asks, the learner answers, and the lab confirms, asks a
 * narrower question, or states the idea and asks for an action on the mat. Everything shown
 * is the server's: the line it is saying, what it heard, and where it is in the exchange.
 *
 * The answer can be typed, or spoken once the learner turns the microphone on. Speech is
 * half duplex: the microphone opens only when the lab has finished saying its line, and
 * closes when the answer ends. Holding Space is push-to-talk, for a noisy room.
 */
export function Reflection({ lesson, onSkip }: { lesson: Lesson; onSkip: () => void }) {
  const send = useTacto((store) => store.send)
  const box = useRef<HTMLInputElement>(null)
  const serverStatus = lesson.reflectionStatus ?? 'asking'
  const asking = serverStatus === 'asking'
  const { step_id: stepId, reflectionLineId: lineId, reflectionAudio: audioUrl } = lesson
  const lineKey = `${stepId}:${lineId}`

  // ---------- the lab's voice ----------
  // Say each new line once. The server is told when it has been heard, or that it could
  // not be played, so the lesson never waits on a sound that did not happen.
  const [heardKey, setHeardKey] = useState('')
  useEffect(() => {
    if (!audioUrl) return
    const audio = new Audio(audioUrl)
    let told = false
    const heard = () => {
      if (told) return
      told = true
      setHeardKey(`${stepId}:${lineId}`)
      useTacto.getState().send({ type: 'reflection_heard', step_id: stepId, line_id: lineId })
    }
    audio.addEventListener('ended', heard)
    audio.addEventListener('error', heard)
    audio.play().catch(heard)
    return () => {
      // A newer line, or the reflection ending, cuts this one short without reporting it.
      told = true
      audio.pause()
    }
  }, [stepId, lineId, audioUrl])
  const labHasFinishedSpeaking = !audioUrl || heardKey === lineKey

  // ---------- the learner's voice ----------
  const [voice, setVoice] = useState(choseVoice)
  const mic = useAnswerMic(stepId, lineId)
  const { state: micState, open: openMic, close: closeMic, talk, release } = mic
  const openedFor = useRef('')
  const mayListen = voice && asking && labHasFinishedSpeaking
  useEffect(() => {
    if (!mayListen) {
      closeMic()
      return
    }
    // Once per line: after the microphone times out it stays closed until asked for.
    if (openedFor.current === lineKey) return
    openedFor.current = lineKey
    void openMic()
  }, [mayListen, lineKey, openMic, closeMic])

  // Push-to-talk: hold Space. Works whether or not the microphone timed out.
  useEffect(() => {
    if (!mayListen) return
    let held = false
    const down = (event: KeyboardEvent) => {
      if (event.code !== 'Space' || isTextEntry(event.target)) return
      // Also on a focused button: Space is the talk key here, not "press this button".
      event.preventDefault()
      if (event.repeat || held) return
      held = true
      talk()
    }
    const letGo = () => {
      if (!held) return
      held = false
      release()
    }
    const up = (event: KeyboardEvent) => {
      if (event.code !== 'Space' || isTextEntry(event.target)) return
      event.preventDefault() // or the browser would click the focused button now
      letGo()
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    // Switching window with the key down: the key-up never arrives here.
    window.addEventListener('blur', letGo)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
      window.removeEventListener('blur', letGo)
      letGo()
    }
  }, [mayListen, talk, release])

  const toggleVoice = () => {
    const on = !voice
    setVoice(on)
    try {
      sessionStorage.setItem(VOICE_CHOICE, on ? 'yes' : 'no')
    } catch {
      // Private browsing: the choice lasts until the page is reloaded.
    }
    if (!on) closeMic()
    else openedFor.current = ''
    // The button keeps the focus after a click, and Space would then press it again.
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const text = box.current?.value.trim() ?? ''
    if (!asking || !text) return
    closeMic()
    send({ type: 'answer_reflection', step_id: stepId, text, line_id: lineId })
  }

  // What the learner sees the lab doing: the server's word, sharpened by what the
  // microphone is doing here, so silence never looks like a crash.
  const status =
    asking && (micState === 'listening' || micState === 'hearing')
      ? 'listening'
      : asking && micState === 'sending'
        ? 'thinking'
        : serverStatus

  return (
    // One blank line above, then everything on the notebook's ruled lines: each row of text or
    // of buttons is a whole number of lines tall (the --line set by the notebook).
    <div className="mt-[var(--line)]">
      <div>
        {/* aria-live: a new line from the lab is read out, the same question again included. */}
        <div role="status" aria-live="polite">
          <p
            className={`m-0 text-[0.75em] font-semibold tracking-wide uppercase ${
              status === 'resolved'
                ? 'text-emerald-700'
                : status === 'listening'
                  ? 'text-rose-700'
                  : 'text-sky-700'
            }`}
          >
            {status === 'listening' && <span aria-hidden="true">● </span>}
            {HEADING[status]}
          </p>
          <p className="m-0 text-[1.1em] font-semibold">
            {lesson.reflectionLine ?? lesson.reflection}
          </p>
          {lesson.reflectionTranscript !== null && (
            <p className="m-0 text-[0.85em] text-stone-600">
              You said: “{lesson.reflectionTranscript || '(nothing heard)'}”
            </p>
          )}
        </div>
        <div className="flex h-[var(--line)] items-center gap-[0.5em] whitespace-nowrap">
          <button
            type="button"
            aria-pressed={voice}
            onClick={toggleVoice}
            title={
              voice
                ? 'Stop using the microphone'
                : 'Answer out loud. What you say is sent to be transcribed and graded.'
            }
            className={`flex h-[calc(var(--line)*0.8)] py-0 cursor-pointer items-center rounded-lg px-[0.7em] text-[0.7em] font-semibold focus-visible:outline-4 focus-visible:outline-sky-600 ${
              voice
                ? 'bg-rose-700 text-white hover:bg-rose-800'
                : 'bg-stone-900/10 hover:bg-stone-900/20'
            }`}
          >
            {voice ? 'Voice on' : 'Answer by voice'}
          </button>
          <button
            type="button"
            onClick={onSkip}
            title="Move on without finishing this question"
            className="flex h-[calc(var(--line)*0.8)] py-0 cursor-pointer items-center rounded-lg bg-stone-900/10 px-[0.7em] text-[0.7em] font-semibold hover:bg-stone-900/20 focus-visible:outline-4 focus-visible:outline-sky-600"
          >
            Skip
          </button>
        </div>
      </div>
      {(asking || serverStatus === 'thinking') && (
        // key: a new line from the lab starts with an empty box.
        <form
          key={lineKey}
          onSubmit={submit}
          className="flex h-[var(--line)] items-center gap-[0.5em] whitespace-nowrap"
        >
          <input
            ref={box}
            type="text"
            aria-label="Your answer"
            placeholder={voice ? 'Or type your answer' : 'Type your answer'}
            autoComplete="off"
            maxLength={600}
            disabled={!asking}
            className="h-[calc(var(--line)*0.8)] py-0 min-w-0 flex-1 rounded-lg border-2 border-stone-500/50 bg-white/70 px-[0.6em] text-[0.75em] text-stone-900 placeholder:text-stone-500 focus-visible:outline-4 focus-visible:outline-sky-600 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!asking}
            className="flex h-[calc(var(--line)*0.8)] py-0 cursor-pointer items-center rounded-lg bg-sky-700 px-[0.8em] text-[0.75em] font-semibold text-white hover:bg-sky-800 focus-visible:outline-4 focus-visible:outline-sky-600 disabled:cursor-default disabled:opacity-50"
          >
            Answer
          </button>
        </form>
      )}
      {(mic.error || (voice && asking)) && (
        <p className="m-0 text-[0.7em] text-stone-600">
          {mic.error ? (
            <span role="alert" className="font-bold text-amber-800">
              {mic.error} Type your answer instead.
            </span>
          ) : voice && asking ? (
            labHasFinishedSpeaking ? (
              MIC_WORDS[micState]
            ) : (
              'The microphone opens when the question has been asked.'
            )
          ) : null}
        </p>
      )}
    </div>
  )
}
