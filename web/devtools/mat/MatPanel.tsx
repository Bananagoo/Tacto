// The virtual mat: play the lesson without paper or a camera. The controls on the left
// change what the product's session sees; the product itself runs on the right, untouched.

import { useEffect, useState } from 'react'
import {
  getMat,
  resetMat,
  setDrawn,
  setFingertip,
  setSlot,
  type MatView,
  type SlotContent,
} from './api'
import MatPad from './MatPad'

const LEARNER_KEY = 'tacto-devtools-learner'

export default function MatPanel() {
  const [mat, setMat] = useState<MatView | null>(null)
  const [error, setError] = useState('')
  // A new nickname is a new learner, which is how the lesson is started from the top.
  const [learner, setLearner] = useState(() => sessionStorage.getItem(LEARNER_KEY) ?? 'dev-1')

  const apply = (change: Promise<MatView>) => {
    change
      .then((view) => {
        setError('')
        setMat(view)
      })
      .catch((reason: unknown) =>
        setError(`Could not reach the server (${String(reason)}). Is make bench running?`),
      )
  }
  useEffect(() => apply(getMat()), [])

  const startOver = () => {
    const next = `dev-${Date.now().toString(36)}`
    sessionStorage.setItem(LEARNER_KEY, next)
    setLearner(next)
    apply(resetMat())
  }

  return (
    <main className="grid gap-6 p-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <section className="flex flex-col gap-4 rounded-xl bg-white/5 p-5">
        <h2 className="text-xl font-semibold">Virtual mat</h2>
        {error && <p className="text-rose-400">{error}</p>}
        {mat && (
          <>
            <MatPad mat={mat} onTouch={(x, y) => apply(setFingertip({ x, y }))} />
            <p className="text-sm opacity-60">
              Click the map to rest a fingertip there.
              <button
                className="ml-2 rounded bg-white/10 px-2 py-0.5 hover:bg-white/20"
                onClick={() => apply(setFingertip(null))}
              >
                Lift finger
              </button>
            </p>

            <h3 className="font-semibold">Draw</h3>
            {mat.layout.drawables.map((drawable) => {
              const drawn = mat.drawn.includes(drawable.id)
              return (
                <label key={drawable.id} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={drawn}
                    onChange={() => apply(setDrawn(drawable.id, !drawn))}
                  />
                  A line across "{drawable.id}"
                </label>
              )
            })}

            <h3 className="font-semibold">Tiles</h3>
            {mat.layout.slots.map((slot) => (
              <label key={slot.id} className="flex items-center gap-2">
                <span className="w-28">Slot "{slot.id}"</span>
                <select
                  className="rounded bg-white/10 px-2 py-1"
                  value={mat.slots[slot.id] ?? 'empty'}
                  onChange={(event) => apply(setSlot(slot.id, event.target.value as SlotContent))}
                >
                  {(['empty', ...slot.accepts] as SlotContent[]).map((content) => (
                    <option key={content}>{content}</option>
                  ))}
                </select>
              </label>
            ))}

            <button
              className="mt-2 rounded bg-white/10 px-3 py-2 hover:bg-white/20"
              onClick={startOver}
            >
              Start over as a new learner
            </button>
            <p className="text-sm opacity-60">Learner: {learner}</p>
          </>
        )}
      </section>

      {/* The product page itself. key: a new learner needs a fresh page and socket. */}
      <iframe
        key={learner}
        title="Tacto"
        src={`/?learner=${encodeURIComponent(learner)}`}
        className="h-[80vh] w-full rounded-xl border border-white/10"
      />
    </main>
  )
}
