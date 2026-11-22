import { useEffect, useState } from 'react'

/** How long a lifted piece stays on screen, fading out. Matches `.piece-out` in index.css. */
export const LINGER_MS = 240

interface Kept<T> {
  key: string
  item: T
}

/**
 * The items that have just gone from a list, kept for a moment so they can fade out instead of
 * blinking off. Only what the camera really saw is ever shown: a ghost is the piece as it last
 * was, and it goes at once if something appears in its place.
 */
export function useLingering<T>(items: readonly T[], keyOf: (item: T) => string): Kept<T>[] {
  const keys = items.map(keyOf)
  const signature = keys.join('|')
  // The list as it was when its set of keys last changed: state messages arrive 15 a second
  // with new objects, so compare the keys, not the array.
  const [seen, setSeen] = useState<{ signature: string; kept: Kept<T>[] }>(() => ({
    signature,
    kept: items.map((item, index) => ({ key: keys[index], item })),
  }))
  const [ghosts, setGhosts] = useState<Kept<T>[]>([])

  if (seen.signature !== signature) {
    const now = new Set(keys)
    const gone = seen.kept.filter((old) => !now.has(old.key))
    setSeen({ signature, kept: items.map((item, index) => ({ key: keys[index], item })) })
    setGhosts((before) => [...before.filter((ghost) => !now.has(ghost.key)), ...gone])
  }

  useEffect(() => {
    if (ghosts.length === 0) return
    const batch = ghosts
    const timer = setTimeout(
      () => setGhosts((current) => current.filter((ghost) => !batch.includes(ghost))),
      LINGER_MS,
    )
    return () => clearTimeout(timer)
  }, [ghosts])

  return ghosts
}
