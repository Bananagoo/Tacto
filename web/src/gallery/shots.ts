// The learner's saved pictures of their circuit, the gallery's contents. They live in this browser (IndexedDB), on this
// machine: nothing is sent to the server or anywhere else, and nothing is saved unless the
// learner pressed the camera button. The gallery page reads them from here.

import { createStore, del, entries, set, type UseStore } from 'idb-keyval'

export interface Shot {
  id: string
  /** When it was taken, as an ISO time. */
  takenAt: string
  png: Blob
}

// Made when first needed, so importing this file touches no storage. Do not rename the database
// or the store below: idb-keyval only makes the store when the database is first created, so a new
// name against a browser that already holds the old one fails with "object store was not found".
// The name says "screenshots" because that is what it was first called; the page says gallery.
let store: UseStore | null = null
const shots = (): UseStore => (store ??= createStore('tacto', 'screenshots'))

/** Keep a picture, stamped with now. Returns what was saved. */
export async function saveShot(png: Blob): Promise<Shot> {
  const takenAt = new Date().toISOString()
  const shot: Shot = { id: `${takenAt}-${Math.random().toString(36).slice(2, 7)}`, takenAt, png }
  await set(shot.id, shot, shots())
  return shot
}

/** Every saved picture, newest first. */
export async function listShots(): Promise<Shot[]> {
  const all = await entries<string, Shot>(shots())
  return all.map(([, shot]) => shot).sort((a, b) => b.takenAt.localeCompare(a.takenAt))
}

export function deleteShot(id: string): Promise<void> {
  return del(id, shots())
}

/** "22 Nov 2026, 02:41", in the viewer's own language and time zone. */
export function whenTaken(takenAt: string): string {
  return new Date(takenAt).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Hand a saved picture to the browser as a download. */
export function downloadShot(shot: Shot): void {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(shot.png)
  link.download = `tacto-circuit-${shot.takenAt.replace(/[:.]/g, '-')}.png`
  link.click()
  URL.revokeObjectURL(link.href)
}
