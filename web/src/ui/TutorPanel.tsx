import type { Phase } from '../contract'
import { useTacto } from '../useTacto'
import { TutorActions } from './TutorActions'

const PHASE_WORD: Record<Phase, string> = {
  build: 'Build',
  predict: 'Predict',
  test: 'Test',
  explain: 'Explain',
  done: 'Finished',
}

const PANEL = 'flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto rounded-3xl bg-white/5 p-8'
const PROMPT = 'm-0 text-4xl leading-tight font-semibold xl:text-5xl'

/**
 * The tutor's side of the lesson: where we are, what the tutor is saying (always as text,
 * whether or not it is also spoken), and what the learner can press.
 */
export function TutorPanel() {
  const connected = useTacto((store) => store.connected)
  const tutor = useTacto((store) => store.state?.tutor)

  if (!tutor) {
    return (
      <section className={PANEL}>
        <p className={PROMPT}>
          {connected ? 'Waiting for the lesson to start.' : 'Connecting to Tacto…'}
        </p>
      </section>
    )
  }

  const { phase } = tutor
  return (
    <section className={PANEL}>
      <p className="m-0 text-2xl font-medium tracking-wide text-stone-300 uppercase">
        {tutor.step_count > 0 && `Step ${tutor.step_index + 1} of ${tutor.step_count} · `}
        {PHASE_WORD[phase]}
      </p>
      {/* Only once the explanation is up: the learner should see the result on the mat first. */}
      {phase === 'explain' && tutor.correct !== null && <Verdict correct={tutor.correct} />}
      {tutor.feedback && <p className="m-0 text-3xl leading-snug">{tutor.feedback}</p>}
      <p className={PROMPT}>{tutor.prompt}</p>
      {tutor.hint && <Hint text={tutor.hint} />}
      <TutorActions
        moment={`${tutor.lesson_id}/${tutor.step_index}/${phase}`}
        phase={phase}
        choices={tutor.choices}
        connected={connected}
      />
    </section>
  )
}

/** Right or wrong, told apart by the mark and the words, with colour only as a third cue. */
function Verdict({ correct }: { correct: boolean }) {
  return (
    <p className={`m-0 text-3xl font-bold ${correct ? 'text-emerald-300' : 'text-amber-300'}`}>
      {correct ? '✓ You predicted it' : '✗ Not what you predicted'}
    </p>
  )
}

function Hint({ text }: { text: string }) {
  return (
    <p className="m-0 rounded-2xl border-2 border-dashed border-stone-100/50 p-5 text-3xl leading-snug">
      <span className="mr-3 font-bold uppercase">Hint</span>
      {text}
    </p>
  )
}
