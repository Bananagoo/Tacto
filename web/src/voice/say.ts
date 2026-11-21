// The tutor's voice. This uses the browser's own speech synthesis, which runs on the
// laptop with no network, so the demo does not depend on Wi-Fi.
// TODO(lesson owner): swap in pre-generated audio files (Tutor.audio_url) for a warmer
// voice; this stays as the fallback.

const RATE = 0.95 // a little slower than default: the room is noisy and the ideas are new

/** Say a line, cutting off whatever was being said: the tutor never talks over itself. */
export function say(line: string, language: string): void {
  window.speechSynthesis.cancel()
  if (!line) return
  const utterance = new SpeechSynthesisUtterance(line)
  utterance.lang = language
  utterance.rate = RATE
  window.speechSynthesis.speak(utterance)
}

export function hush(): void {
  window.speechSynthesis.cancel()
}
