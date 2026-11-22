import type { Circuit } from '../contract'
import { dotToPoint, type Point } from './grid'

/** How close, in SVG units (a dot pitch is 100), the pointer must be to read a part or a wire. */
const PART_REACH = 45
const WIRE_REACH = 30

/** What the multimeter reads at one spot. Every number is the server's; none is worked out here. */
export interface Reading {
  /** Amps through whatever the probe touches. */
  current: number
  /** Volts across it: a part's drop, and about nothing for a plain wire. */
  volts: number
  /** The wire's place key, as `placeKeys` names it, so the bench can light it. Null for a part. */
  wireKey: string | null
  /** The wire is on the shorted path. */
  short: boolean
}

function distanceToSegment(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const lengthSquared = dx * dx + dy * dy
  // Two identical ends are a point, not a division by zero.
  const along = lengthSquared === 0 ? 0 : ((p.x - a.x) * dx + (p.y - a.y) * dy) / lengthSquared
  const t = Math.min(1, Math.max(0, along))
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))
}

/**
 * The reading under the pointer, or null when it is over nothing. A part wins over a wire,
 * because a part sits on its wires. `wireKeys` are the keys the bench draws the wires under.
 */
export function readingAt(
  point: Point,
  circuit: Circuit | undefined,
  wireKeys: readonly string[],
): Reading | null {
  if (!circuit) return null

  let nearest: { distance: number; reading: Reading } | null = null
  for (const part of circuit.parts) {
    const distance = distanceToSegment(point, dotToPoint(part.a), dotToPoint(part.b))
    if (distance <= PART_REACH && (!nearest || distance < nearest.distance)) {
      nearest = {
        distance,
        reading: { current: part.current, volts: part.voltage, wireKey: null, short: false },
      }
    }
  }
  if (nearest) return nearest.reading

  circuit.wires.forEach((wire, index) => {
    const distance = distanceToSegment(point, dotToPoint(wire.a), dotToPoint(wire.b))
    if (distance <= WIRE_REACH && (!nearest || distance < nearest.distance)) {
      nearest = {
        distance,
        reading: {
          current: wire.current,
          volts: 0,
          wireKey: wireKeys[index] ?? null,
          short: wire.overloaded,
        },
      }
    }
  })
  return nearest ? (nearest as { distance: number; reading: Reading }).reading : null
}

/**
 * The reading of one piece by its id, for the fingertip on the paper: the server says which
 * piece the finger is on. Null when it is on nothing the circuit lists.
 */
export function readingOf(
  id: string | null,
  circuit: Circuit | undefined,
  wireKeys: readonly string[],
): Reading | null {
  if (!circuit || id === null) return null
  const part = circuit.parts.find((candidate) => candidate.id === id)
  if (part) return { current: part.current, volts: part.voltage, wireKey: null, short: false }
  const index = circuit.wires.findIndex((candidate) => candidate.id === id)
  if (index < 0) return null
  const wire = circuit.wires[index]
  return {
    current: wire.current,
    volts: 0,
    wireKey: wireKeys[index] ?? null,
    short: wire.overloaded,
  }
}
