import { create } from 'zustand'

interface VoiceStore {
  /** Whether the tutor speaks. Off until the learner turns it on: browsers only allow
   * speech after a click, so the switch is also what unlocks it. */
  speaking: boolean
  setSpeaking: (speaking: boolean) => void
}

export const useVoice = create<VoiceStore>((set) => ({
  speaking: false,
  setSpeaking: (speaking) => set({ speaking }),
}))

/** False in browsers with no speech synthesis; the tutor's lines are always on screen too. */
export const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window
