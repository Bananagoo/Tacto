import type { Phase } from '../contract'
import { BigButton } from './BigButton'
import { useSendOnce } from './useSendOnce'
import { toWords } from './words'

interface TutorActionsProps {
  /** Names this point in the lesson; a press is accepted once per moment. */
  moment: string
  phase: Phase
  choices: string[]
  connected: boolean
}

/**
 * What the learner can press right now: a prediction while predicting, Next while testing
 * or reading the explanation, nothing otherwise. The buttons are always there in the
 * predict phase, whether or not voice is working.
 */
export function TutorActions({ moment, phase, choices, connected }: TutorActionsProps) {
  const { waiting, sendOnce } = useSendOnce(moment)
  const disabled = waiting || !connected

  if (phase === 'predict') {
    return (
      <div className="flex flex-wrap gap-4">
        {choices.map((choice) => (
          <BigButton
            key={choice}
            label={toWords(choice)}
            disabled={disabled}
            onPress={() => sendOnce({ type: 'answer', choice, via: 'button' })}
          />
        ))}
      </div>
    )
  }
  if (phase === 'test' || phase === 'explain') {
    return (
      <div>
        <BigButton label="Next" disabled={disabled} onPress={() => sendOnce({ type: 'next' })} />
      </div>
    )
  }
  return null
}
