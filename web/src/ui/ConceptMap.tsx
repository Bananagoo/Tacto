import { useShallow } from 'zustand/react/shallow'
import type { Concept, Mastery } from '../contract'
import { useTacto } from '../useTacto'
import { toWords } from './words'

// Each level differs in its mark, its words, its border and its fill, so the three can be
// told apart without colour.
const LOOK: Record<Mastery, { mark: string; words: string; className: string }> = {
  unseen: {
    mark: '○',
    words: 'Not yet',
    className: 'border-dashed border-stone-100/40 text-stone-300',
  },
  shaky: {
    mark: '◐',
    words: 'Getting there',
    className: 'border-solid border-amber-300 text-amber-100',
  },
  solid: {
    mark: '✓',
    words: 'Got it',
    className: 'border-solid border-emerald-300 bg-emerald-300 text-stone-900',
  },
}

const NO_CONCEPTS: Partial<Record<Concept, Mastery>> = {}

/** The learner's concepts and how well each one is known. */
export function ConceptMap() {
  // Shallow comparison: the map arrives as a new object fifteen times a second but its
  // contents change only when the learner answers.
  const learner = useTacto(useShallow((store) => store.state?.learner ?? NO_CONCEPTS))
  const concepts = Object.entries(learner)

  return (
    <section className="rounded-3xl bg-white/5 p-6">
      <h2 className="m-0 mb-4 text-2xl font-medium tracking-wide text-stone-300 uppercase">
        What you know
      </h2>
      {concepts.length === 0 ? (
        <p className="m-0 text-2xl text-stone-300">Ideas appear here as you meet them.</p>
      ) : (
        <ul className="m-0 flex list-none flex-wrap gap-3 p-0">
          {concepts.map(([concept, mastery]) => {
            const look = LOOK[mastery ?? 'unseen']
            return (
              <li
                key={concept}
                className={`flex items-baseline gap-3 rounded-2xl border-4 px-5 py-3 ${look.className}`}
              >
                <span className="text-3xl font-bold" aria-hidden="true">
                  {look.mark}
                </span>
                <span className="text-3xl font-semibold">{toWords(concept)}</span>
                <span className="text-xl">{look.words}</span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
