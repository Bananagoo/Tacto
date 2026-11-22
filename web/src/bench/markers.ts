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

// A line is a few points with straight pieces between them, so before cutting it is filled in
// with a point every few units; otherwise a quick stroke could pass through the eraser untouched.
const CUT_STEP = 4

function filledIn(points: readonly Point[]): Point[] {
  const out: Point[] = points.length > 0 ? [points[0]] : []
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]
    const b = points[i]
    const pieces = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / CUT_STEP))
    for (let step = 1; step <= pieces; step++) {
      const t = step / pieces
      out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t })
    }
  }
  return out
}

/**
 * What is left of a line after the eraser at `spot` has taken the part under it: nothing, the
 * same line if it was not touched, or one or two shorter lines either side of the cut. A bit
 * too short to see (a single point left over) is dropped.
 */
export function eraseFromStroke(stroke: Stroke, spot: Point, radius: number): Stroke[] {
  if (!strokeTouches(stroke, spot, radius)) return [stroke]
  const pieces: Point[][] = []
  let run: Point[] = []
  for (const point of filledIn(stroke.points)) {
    if (Math.hypot(point.x - spot.x, point.y - spot.y) <= radius) {
      if (run.length > 0) pieces.push(run)
      run = []
    } else run.push(point)
  }
  if (run.length > 0) pieces.push(run)
  return pieces
    .filter((points) => points.length >= 2)
    .map((points) => ({ color: stroke.color, points }))
}
