import { useEffect } from 'react'
import { useTacto } from '../useTacto'
import { hush, say } from './say'
import { canSpeak, useVoice } from './voiceStore'

const LANGUAGE = 'en'

/**
 * Speak the tutor's lines as they change: the reply to a wrong idea first, then the
 * prompt, then a hint when one appears. Each is read from the store as a plain string,
 * so the fifteen state messages a second do not restart a sentence.
 */
export function useSpokenTutor() {
  const speaking = useVoice((store) => store.speaking)
  const prompt = useTacto((store) => store.state?.tutor.prompt ?? '')
  const feedback = useTacto((store) => store.state?.tutor.feedback ?? '')
  const hint = useTacto((store) => store.state?.tutor.hint ?? '')

  useEffect(() => {
    if (!canSpeak || !speaking) return
    say([feedback, prompt].filter(Boolean).join(' '), LANGUAGE)
  }, [speaking, prompt, feedback])

  useEffect(() => {
    if (!canSpeak || !speaking || !hint) return
    say(hint, LANGUAGE)
  }, [speaking, hint])

  // Turning the voice off, or leaving the page, stops it mid-sentence.
  useEffect(() => {
    if (!canSpeak || speaking) return
    hush()
  }, [speaking])
  useEffect(() => () => (canSpeak ? hush() : undefined), [])
}
