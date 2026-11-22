// The mat's dot grid in SVG units. Everything the bench draws is placed through this file,
// so a change to the paper kit's geometry is a change here and nowhere else.

import type { Dot } from '../contract'

// TODO(vision owner): placeholder until the paper kit's geometry is final.
export const GRID_COLS = 9
export const GRID_ROWS = 6

/** SVG units between neighbouring dots. Every size in the bench is chosen against this. */
export const DOT_PITCH = 100

// Room around the outer dots, so a part on an edge row is not clipped. The LED's dome stands
// about 120 above its wire, so the top margin has to be at least that.
const MARGIN = 130

export const VIEW_WIDTH = (GRID_COLS - 1) * DOT_PITCH + 2 * MARGIN
export const VIEW_HEIGHT = (GRID_ROWS - 1) * DOT_PITCH + 2 * MARGIN

export interface Point {
  x: number
  y: number
}

export function dotToPoint([col, row]: Dot): Point {
  return { x: MARGIN + col * DOT_PITCH, y: MARGIN + row * DOT_PITCH }
}

function clampUnit(value: number): number {
  return Math.min(1, Math.max(0, value))
}

/**
 * Mat position to SVG. As in the contract, 0..1 runs from the first dot column or row to
 * the last. Clamped to stay on the mat.
 */
export function matToPoint(x: number, y: number): Point {
  return {
    x: MARGIN + clampUnit(x) * (GRID_COLS - 1) * DOT_PITCH,
    y: MARGIN + clampUnit(y) * (GRID_ROWS - 1) * DOT_PITCH,
  }
}

export interface Span {
  length: number
  angleDeg: number
}

/**
 * Length and direction from `a` to `b`. Two identical points give length 0 and angle 0,
 * never NaN: the camera can report a part whose two ends landed on the same dot.
 */
export function spanBetween(a: Point, b: Point): Span {
  const dx = b.x - a.x
  const dy = b.y - a.y
  return { length: Math.hypot(dx, dy), angleDeg: (Math.atan2(dy, dx) * 180) / Math.PI }
}

/**
 * One React key per item, stable while the item stays in the list. Items are keyed by where
 * they are; a repeat of the same place gets a counter so keys never collide.
 */
export function placeKeys(items: readonly { a: Dot; b: Dot }[]): string[] {
  const seen = new Map<string, number>()
  return items.map(({ a, b }) => {
    const place = `${a[0]},${a[1]}-${b[0]},${b[1]}`
    const repeat = seen.get(place) ?? 0
    seen.set(place, repeat + 1)
    return repeat === 0 ? place : `${place}#${repeat}`
  })
}
