// Two things live here.
//
// 1. The wire contract: a mirror of server/tacto/contract.py, which is the source of
//    truth (JSON schema in contract/). `ServerState` is the one message the server sends;
//    `SetVoltage` is the one the page sends back. Change both sides in the same commit.
//
// 2. The page's own picture of that state (`State`, `Part`, `Wire`, `Probe`): the shapes
//    the bench, the multimeter and the haptics were built on. `fromServer.ts` turns a
//    ServerState into one, and is the only place that knows both.

export type Dot = [col: number, row: number]

// ---------- the wire contract: server -> web ----------

export type PieceType = 'wire' | 'battery' | 'bulb' | 'resistor' | 'switch'
export type ServerCircuitStatus = 'working' | 'open' | 'shorted'

export interface ServerPiece {
  /** The segment the piece lies on, "c,r-c,r". */
  id: string
  type: PieceType
  /** For a battery, the positive end. */
  a: Dot
  b: Dot
  /** Switches only. The learner swaps the open piece for the closed one. */
  closed: boolean | null
  /** Amps, signed: positive flows a -> b. */
  current: number
  /** Volts across the piece; 0 for a wire and a closed switch. */
  voltage: number
  /** Bulbs only, 0 to 1. */
  brightness: number | null
  /** On the shorted path. */
  shorted: boolean
}

export interface ServerState {
  type: 'state'
  version: number
  seq: number
  t: number
  source: 'camera' | 'replay' | 'manual'
  /** False while the camera cannot find the mat; the pieces hold their last values. */
  mat_visible: boolean
  grid: { cols: number; rows: number }
  pieces: ServerPiece[]
  circuit: {
    status: ServerCircuitStatus
    voltage: number
    total_current: number
    shorted_path: string[]
  }
  touch: {
    present: boolean
    x: number
    y: number
    piece_id: string | null
    pulse_hz: number
    /** How hard to vibrate, 0 to 1. Rises and falls with pulse_hz. */
    strength: number
    buzz: boolean
  }
  lesson: {
    lesson_id: string
    step_id: string
    step_index: number
    step_count: number
    prompt: string
    step_done: boolean
    lesson_done: boolean
  }
}

// ---------- the wire contract: web -> server ----------

export const MAX_VOLTS = 9

export interface SetVoltage {
  type: 'set_voltage'
  volts: number
}

// ---------- the page's picture of the state ----------

export type PartKind = 'battery' | 'bulb' | 'resistor' | 'switch'
export type CircuitStatus = 'empty' | 'open' | 'closed' | 'short'
export type HapticPattern = 'tick' | 'short'

export interface Part {
  id: string
  kind: PartKind
  /** For a battery, the positive terminal. */
  a: Dot
  b: Dot
  closed: boolean | null
  current: number
  voltage: number
  brightness: number
}

export interface Wire {
  /** The piece's id on the server: its segment. */
  id: string
  a: Dot
  b: Dot
  current: number
  overloaded: boolean
}

export interface Circuit {
  status: CircuitStatus
  source_voltage: number
  total_current: number
  parts: Part[]
  wires: Wire[]
}

export interface Probe {
  present: boolean
  x: number
  y: number
  /** The id of the piece under the fingertip, part or wire. */
  on: string | null
  current: number
  pulse_hz: number
  /** How hard to vibrate, 0 to 1. */
  strength: number
  buzz: boolean
}

export interface Lesson {
  step_index: number
  step_count: number
  prompt: string
  step_done: boolean
  lesson_done: boolean
}

export interface State {
  type: 'state'
  t: number
  source: 'camera' | 'replay' | 'manual'
  mat_visible: boolean
  circuit: Circuit
  probe: Probe
  lesson: Lesson
  tutor: Tutor
  learner: Partial<Record<Concept, Mastery>>
}

export type ClientMessage = SetVoltage | ParkedClientMessage

// ---------- parked ----------
// The tutor, the concept map and the voice are out of the product for now (CLAUDE.md,
// "Parked"). The server sends nothing for them and ignores these messages. The types stay
// so that the components kept in ui/ and voice/ still compile; nothing in the layout uses them.

/** A concept id from the lesson being taught. */
export type Concept = string
export type Mastery = 'unseen' | 'shaky' | 'solid'
export type Zone = 'too_easy' | 'productive' | 'stuck'
export type Phase = 'build' | 'predict' | 'test' | 'explain' | 'done'
export type Topology = 'none' | 'single' | 'series' | 'parallel' | 'mixed'

export interface Tutor {
  lesson_id: string
  challenge_id: string
  step_index: number
  step_count: number
  phase: Phase
  prompt: string
  choices: string[]
  correct: boolean | null
  feedback: string
  hint: string
  audio_url: string | null
  zone: Zone
  score: number
}

export type ParkedClientMessage =
  | { type: 'wheel'; steps: number }
  | { type: 'answer'; choice: string; via: 'voice' | 'button' }
  | { type: 'calibrate_touch'; corner: 0 | 1 | 2 | 3 }
  | { type: 'next' }
