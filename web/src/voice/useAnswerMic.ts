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
 * `talk` and `release` are the push-to-talk pair for a noisy room: the clip is whatever was
 * said between them, whatever the detector thought.
 */
export function useAnswerMic(stepId: string) {
  const [state, setState] = useState<MicState>('off')
  const [error, setError] = useState('')
  const vad = useRef<MicVAD | null>(null)
  const loading = useRef<Promise<MicVAD> | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  // The step a clip belongs to is the one being asked when the clip ends.
  const step = useRef(stepId)
  useEffect(() => {
    step.current = stepId
  }, [stepId])

  const sendClip = useCallback(async (samples: Float32Array) => {
    setState('sending')
    try {
      const { utils } = await import('@ricky0123/vad-web')
      // 16-bit PCM: a third of the size of the detector's own 32-bit samples.
      const wav = utils.encodeWAV(samples, 1, 16000, 1, 16)
      await fetch(`/voice/answer?step_id=${encodeURIComponent(step.current)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'audio/wav' },
        body: wav,
      })
    } catch (failure) {
      console.error('mic: the answer could not be sent', failure)
    }
    // Whatever happened, the state from the server says what comes next.
    setState('off')
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
        // Push-to-talk: letting go of the key ends the answer there and then.
        submitUserSpeechOnPause: true,
        onSpeechStart: () => setState('hearing'),
        onVADMisfire: () => setState('listening'),
        onSpeechEnd: (samples) => {
          clearTimeout(timer.current)
          void vad.current?.pause()
          void sendClip(samples)
        },
      }).then((created) => {
        vad.current = created
        return created
      }),
    )
    return loading.current
  }, [sendClip])

  const close = useCallback(() => {
    clearTimeout(timer.current)
    void vad.current?.pause()
    setState((now) => (now === 'sending' || now === 'failed' ? now : 'off'))
  }, [])

  const open = useCallback(
    async (limitMs: number | null = LISTEN_MAX_MS) => {
      setError('')
      setState('starting')
      try {
        const detector = await load()
        await detector.start()
        setState('listening')
        clearTimeout(timer.current)
        if (limitMs !== null) timer.current = setTimeout(close, limitMs)
      } catch (failure) {
        loading.current = null
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

  // Let go of the microphone when the reflection goes away.
  useEffect(
    () => () => {
      clearTimeout(timer.current)
      void vad.current?.destroy()
      vad.current = null
      loading.current = null
    },
    [],
  )

  const talk = useCallback(() => void open(null), [open])
  return { state, error, open, close, talk, release: close }
}
