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

/** How close, in SVG units, the eraser must come to a line to take it away: three sizes. */
export const ERASER_SIZES = [
  { name: 'Small', radius: 15 },
  { name: 'Medium', radius: 30 },
  { name: 'Large', radius: 60 },
] as const
export const DEFAULT_ERASER_RADIUS: number = ERASER_SIZES[1].radius

function distanceToSegment(spot: Point, a: Point, b: Point): number {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const lengthSquared = dx * dx + dy * dy
  // A single point (a dot) is a segment of no length, not a division by zero.
  const along =
    lengthSquared === 0 ? 0 : ((spot.x - a.x) * dx + (spot.y - a.y) * dy) / lengthSquared
  const t = Math.min(1, Math.max(0, along))
  return Math.hypot(spot.x - (a.x + t * dx), spot.y - (a.y + t * dy))
}

/** Whether the eraser at `spot` touches this line anywhere along it. */
export function strokeTouches(stroke: Stroke, spot: Point, radius: number): boolean {
  const { points } = stroke
  if (points.length === 1) return distanceToSegment(spot, points[0], points[0]) <= radius
  return points.slice(1).some((point, i) => distanceToSegment(spot, points[i], point) <= radius)
}
