// The gallery: every picture of a circuit the learner saved with the camera tool, newest
// first, each with the date and time it was taken. They are kept in this browser only. Reached from
// the sticky note on the launch page.

import { useCallback, useEffect, useState } from 'react'
import { deleteShot, downloadShot, listShots, whenTaken, type Shot } from '../gallery/shots'

const BUTTON =
  'cursor-pointer rounded-xl border-4 border-[#1f2a14] px-5 py-1 text-2xl text-[#1f2a14] hover:bg-[#1f2a14] hover:text-[#dcefb0] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-sky-600'

export function Gallery({ onBack }: { onBack: () => void }) {
  const [shots, setShots] = useState<Shot[] | null>(null)
  const [error, setError] = useState('')
  const [urls, setUrls] = useState<Record<string, string>>({})
  const [viewing, setViewing] = useState<Shot | null>(null)

  const load = useCallback(() => {
    listShots().then(
      (found) => setShots(found),
      (reason: unknown) => setError(`Could not open the gallery (${String(reason)})`),
    )
  }, [])
  useEffect(load, [load])

  // A web address for each picture, made when the list changes and let go of afterwards.
  useEffect(() => {
    const made = Object.fromEntries(
      (shots ?? []).map((shot) => [shot.id, URL.createObjectURL(shot.png)]),
    )
    setUrls(made)
    return () => Object.values(made).forEach((url) => URL.revokeObjectURL(url))
  }, [shots])

  const remove = (shot: Shot) => {
    setViewing(null)
    deleteShot(shot.id).then(load, (reason: unknown) =>
      setError(`Could not delete it (${String(reason)})`),
    )
  }

  return (
    <div className="h-full overflow-y-auto bg-[#dcefb0] p-8 font-['Patrick_Hand'] text-[#1f2a14]">
      <header className="mx-auto grid max-w-6xl grid-cols-[1fr_auto_1fr] items-center gap-6">
        <button type="button" onClick={onBack} className={`${BUTTON} justify-self-start`}>
          ← Back
        </button>
        <h1 className="m-0 text-center text-7xl leading-none">Gallery</h1>
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        {error && <p className="text-3xl text-red-800">{error}</p>}
        {shots === null && !error && <p className="text-3xl">Opening the gallery…</p>}
        {shots?.length === 0 && (
          <p className="text-3xl">
            Nothing in the gallery yet. Open the lab and press the camera tool to keep a picture of
            your circuit.
          </p>
        )}
        <ul className="m-0 grid list-none grid-cols-1 gap-6 p-0 sm:grid-cols-2 lg:grid-cols-3">
          {shots?.map((shot) => (
            <li key={shot.id} className="flex flex-col gap-3 rounded-2xl bg-white p-4 shadow-md">
              <button
                type="button"
                onClick={() => setViewing(shot)}
                aria-label={`Open the picture from ${whenTaken(shot.takenAt)}`}
                className="cursor-pointer rounded-xl focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-sky-600"
              >
                <img src={urls[shot.id]} alt="" className="w-full rounded-xl" />
              </button>
              <p className="m-0 text-3xl">{whenTaken(shot.takenAt)}</p>
              <div className="flex gap-3">
                <button type="button" onClick={() => downloadShot(shot)} className={BUTTON}>
                  Download
                </button>
                <button type="button" onClick={() => remove(shot)} className={BUTTON}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </main>

      {viewing && (
        <div
          role="dialog"
          aria-label={`Picture from ${whenTaken(viewing.takenAt)}`}
          className="fixed inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-black/80 p-6"
          onClick={() => setViewing(null)}
        >
          <img
            src={urls[viewing.id]}
            alt=""
            className="max-h-[80vh] max-w-full rounded-xl"
            onClick={(event) => event.stopPropagation()}
          />
          <p className="m-0 text-3xl text-white">{whenTaken(viewing.takenAt)}</p>
          <button type="button" onClick={() => setViewing(null)} className={`${BUTTON} bg-white`}>
            Close
          </button>
        </div>
      )}
    </div>
  )
}
