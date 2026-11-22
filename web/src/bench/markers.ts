import type { Point } from './grid'

/** A line drawn with the marker. It lives only on this page: the circuit never sees it. */
export interface Stroke {
  color: string
  points: Point[]
}

// Four inks that show on the green mat: white, yellow, pink and near-black.
export const MARKER_COLORS = [
  { name: 'White', value: '#f8fafc' },
  { name: 'Yellow', value: '#fde047' },
  { name: 'Pink', value: '#fb7185' },
  { name: 'Black', value: '#052e16' },
] as const

/** SVG units. Thick enough to read from across the room. */
export const MARKER_WIDTH = 8

/** The path for a stroke. A stroke of one point is a dot, drawn by the round line cap. */
export function strokePath(points: readonly Point[]): string {
  if (points.length === 0) return ''
  const [first, ...rest] = points
  const lines = rest.length === 0 ? ['l 0 0'] : rest.map((point) => `L ${point.x} ${point.y}`)
  return [`M ${first.x} ${first.y}`, ...lines].join(' ')
}
