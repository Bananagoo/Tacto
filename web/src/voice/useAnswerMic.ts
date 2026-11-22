import { useCallback, useEffect, useRef, useState } from 'react'
import type { MicVAD } from '@ricky0123/vad-web'

/**
 * off: the microphone is closed.  starting: it is being opened.  listening: it is open and
 * waiting for speech.  hearing: the learner is speaking.  sending: the clip is with the
 * server, being transcribed.  failed: it could not be opened (see `error`).
 */
export type MicState = 'off' | 'starting' | 'listening' | 'hearing' | 'sending' | 'failed'

// TODO(front end owner): tune all three in the demo room.
/** The microphone closes by itself after this long with no answer (half duplex, 15 s). */
const LISTEN_MAX_MS = 15_000
/** Silence that ends an answer. Short enough to feel prompt, long enough for a pause to think. */
const END_OF_ANSWER_MS = 900
/** Shorter sounds are a cough or a click, not an answer. */
const SHORTEST_ANSWER_MS = 250

/**
 * The learner's microphone for one spoken answer at a time. Voice detection (Silero, in the
 * browser) decides when the answer starts and ends; that stretch of sound goes to the server
 * as one clip, is transcribed there, and comes back through the state like a typed answer.
 *
 * Half duplex: the caller opens the microphone only once the lab has finished speaking, and
 * it closes when the answer ends, when `LISTEN_MAX_MS` passes, or when `close` is called.
 * `close` throws away anything half heard. `talk` and `release` are the push-to-talk pair
 * for a noisy room: letting go sends what the detector heard up to that moment.
 *
 * A clip is labelled with the step and line that were being asked when the microphone
 * opened, so one that arrives after the lab has moved on is dropped by the server.
 */
export function useAnswerMic(stepId: string, lineId: number) {
  const [state, setState] = useState<MicState>('off')
  const [error, setError] = useState('')
  const vad = useRef<MicVAD | null>(null)
  const loading = useRef<Promise<MicVAD> | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  // Every open and every close takes a new number. An open that finds the number changed
  // when its microphone finally arrives knows it is no longer wanted, and shuts it again.
  const turn = useRef(0)
  const gone = useRef(false)
  const asked = useRef({ step: stepId, line: lineId })
  const opened = useRef({ step: stepId, line: lineId })
  useEffect(() => {
    asked.current = { step: stepId, line: lineId }
  }, [stepId, lineId])

  const sendClip = useCallback(async (samples: Float32Array) => {
    const { step, line } = opened.current
    setState('sending')
    try {
      const { utils } = await import('@ricky0123/vad-web')
      // 16-bit PCM: a third of the size of the detector's own 32-bit samples.
      const wav = utils.encodeWAV(samples, 1, 16000, 1, 16)
      await fetch(`/voice/answer?step_id=${encodeURIComponent(step)}&line_id=${line}`, {
        method: 'POST',
        headers: { 'Content-Type': 'audio/wav' },
        body: wav,
      })
    } catch (failure) {
      console.error('mic: the answer could not be sent', failure)
    }
    // Whatever happened, the state from the server says what comes next.
    if (!gone.current) setState('off')
  }, [])

  const load = useCallback(() => {
    loading.current ??= import('@ricky0123/vad-web').then(({ MicVAD }) =>
      MicVAD.new({
        model: 'legacy',
        baseAssetPath: '/vad/',
        onnxWASMBasePath: '/vad/',
        startOnLoad: false,
        redemptionMs: END_OF_ANSWER_MS,
        minSpeechMs: SHORTEST_ANSWER_MS,
        // Off except during push-to-talk: closing the microphone must not send a clip.
        submitUserSpeechOnPause: false,
        onSpeechStart: () => {
          if (!gone.current) setState('hearing')
        },
        onVADMisfire: () => {
          if (!gone.current) setState('listening')
        },
        onSpeechEnd: (samples) => {
          clearTimeout(timer.current)
          turn.current += 1
          void vad.current?.pause()
          if (!gone.current) void sendClip(samples)
        },
      }).then(async (created) => {
        if (gone.current) {
          // The reflection went away while the model was loading: nothing must be left open.
          await created.destroy()
          throw new Error('the microphone is no longer wanted')
        }
        vad.current = created
        return created
      }),
    )
    return loading.current
  }, [sendClip])

  /** Shut the microphone and throw away anything half heard. */
  const close = useCallback(() => {
    turn.current += 1
    clearTimeout(timer.current)
    vad.current?.setOptions({ submitUserSpeechOnPause: false })
    void vad.current?.pause()
    setState((now) => (now === 'sending' || now === 'failed' ? now : 'off'))
  }, [])

  const open = useCallback(
    async (limitMs: number | null = LISTEN_MAX_MS, pushToTalk = false) => {
      const mine = ++turn.current
      const wanted = () => mine === turn.current && !gone.current
      setError('')
      setState('starting')
      try {
        const detector = await load()
        if (!wanted()) return
        detector.setOptions({ submitUserSpeechOnPause: pushToTalk })
        opened.current = asked.current
        await detector.start()
        if (!wanted()) {
          // Closed, or the key let go, while the microphone was still opening.
          detector.setOptions({ submitUserSpeechOnPause: false })
          await detector.pause()
          return
        }
        setState('listening')
        clearTimeout(timer.current)
        if (limitMs !== null) timer.current = setTimeout(close, limitMs)
      } catch (failure) {
        loading.current = null
        if (!wanted()) return
        setError(
          failure instanceof Error && failure.name === 'NotAllowedError'
            ? 'The browser was not allowed to use the microphone.'
            : 'The microphone could not be opened.',
        )
        setState('failed')
      }
    },
    [load, close],
  )

  /** Push-to-talk: the key went down. */
  const talk = useCallback(() => void open(null, true), [open])

  /** Push-to-talk: the key came up. Sends what was heard while it was down. */
  const release = useCallback(() => {
    turn.current += 1
    clearTimeout(timer.current)
    const detector = vad.current
    if (!detector) {
      setState('off')
      return
    }
    void detector.pause().then(() => detector.setOptions({ submitUserSpeechOnPause: false }))
    setState((now) => (now === 'sending' || now === 'failed' ? now : 'off'))
  }, [])

  // Let go of the microphone when the reflection goes away.
  useEffect(() => {
    gone.current = false
    return () => {
      gone.current = true
      turn.current += 1
      clearTimeout(timer.current)
      const detector = vad.current
      vad.current = null
      loading.current = null
      void detector?.destroy().catch(() => undefined)
    }
  }, [])

  return { state, error, open, close, talk, release }
}
