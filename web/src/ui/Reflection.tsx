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

/** True for the keys' targets that already use Space or Enter themselves. */
function isControl(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      target.closest('input, textarea, select, button, a, [role="textbox"]') !== null)
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
  const mic = useAnswerMic(stepId)
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
      if (event.code !== 'Space' || event.repeat || isControl(event.target)) return
      event.preventDefault()
      held = true
      talk()
    }
    const up = (event: KeyboardEvent) => {
      if (event.code !== 'Space' || !held) return
      held = false
      release()
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
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
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const text = box.current?.value.trim() ?? ''
    if (!asking || !text) return
    closeMic()
    send({ type: 'answer_reflection', step_id: stepId, text })
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
    <div className="mt-4 border-t border-white/15 pt-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        {/* aria-live: a new line from the lab is read out, the same question again included. */}
        <div role="status" aria-live="polite" className="min-w-0 flex-1">
          <p
            className={`m-0 text-sm font-semibold tracking-wide uppercase ${
              status === 'resolved'
                ? 'text-emerald-300'
                : status === 'listening'
                  ? 'text-rose-300'
                  : 'text-sky-300'
            }`}
          >
            {status === 'listening' && <span aria-hidden="true">● </span>}
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
        <div className="flex gap-3">
          <button
            type="button"
            aria-pressed={voice}
            onClick={toggleVoice}
            title={
              voice
                ? 'Stop using the microphone'
                : 'Answer out loud. What you say is sent to be transcribed and graded.'
            }
            className={`cursor-pointer rounded-xl px-4 py-3 text-lg font-semibold focus-visible:outline-4 focus-visible:outline-sky-300 ${
              voice
                ? 'bg-rose-300 text-rose-950 hover:bg-rose-200'
                : 'bg-white/15 hover:bg-white/25'
            }`}
          >
            {voice ? 'Voice on' : 'Answer by voice'}
          </button>
          <button
            type="button"
            onClick={onSkip}
            title="Move on without finishing this question"
            className="cursor-pointer rounded-xl bg-white/15 px-4 py-3 text-lg font-semibold hover:bg-white/25 focus-visible:outline-4 focus-visible:outline-sky-300"
          >
            Skip
          </button>
        </div>
      </div>
      {(asking || serverStatus === 'thinking') && (
        // key: a new line from the lab starts with an empty box.
        <form key={lineKey} onSubmit={submit} className="mt-3 flex flex-wrap gap-3">
          <input
            ref={box}
            type="text"
            aria-label="Your answer"
            placeholder={voice ? 'Or type your answer' : 'Type your answer'}
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
      <p className="m-0 mt-2 text-sm text-stone-300">
        {mic.error ? (
          <span role="alert" className="font-bold text-amber-300">
            {mic.error} Type your answer instead.
          </span>
        ) : voice && asking ? (
          labHasFinishedSpeaking ? (
            MIC_WORDS[micState]
          ) : (
            'The microphone opens when the question has been asked.'
          )
        ) : (
          'What you answer is transcribed and graded, and the words are saved on this laptop. The sound is not kept.'
        )}
      </p>
    </div>
  )
}
