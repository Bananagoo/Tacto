// Mirror of server/tacto/contract.py. That file is the source of truth:
// change both in the same commit.

export type Dot = [col: number, row: number]

export type PartKind = 'battery' | 'bulb' | 'resistor' | 'switch'
export type CircuitStatus = 'empty' | 'open' | 'closed' | 'short'
export type Concept = 'closed_loop' | 'current' | 'voltage' | 'resistance' | 'series' | 'parallel'
export type Mastery = 'unseen' | 'shaky' | 'solid'
export type Zone = 'too_easy' | 'productive' | 'stuck'
export type Phase = 'build' | 'predict' | 'test' | 'explain' | 'done'
export type HapticPattern = 'tick' | 'nudge' | 'short' | 'success'

// ---------- server -> web ----------

export interface Part {
  id: string
  kind: PartKind
  a: Dot
  b: Dot
  closed: boolean | null
  current: number
  voltage: number
  brightness: number
}

export interface Wire {
  a: Dot
  b: Dot
  current: number
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
  on: string | null
  current: number
  pulse_hz: number
}

export interface Tutor {
  challenge_id: string
  phase: Phase
  prompt: string
  choices: string[]
  audio_url: string | null
  zone: Zone
  score: number
}

export interface State {
  type: 'state'
  t: number
  source: 'mock' | 'replay' | 'camera'
  circuit: Circuit
  probe: Probe
  tutor: Tutor
  learner: Partial<Record<Concept, Mastery>>
}

export interface Haptic {
  type: 'haptic'
  pattern: HapticPattern
}

export type ServerMessage = State | Haptic

// ---------- web -> server ----------

export type ClientMessage =
  | { type: 'wheel'; steps: number }
  | { type: 'answer'; choice: string; via: 'voice' | 'button' }
  | { type: 'calibrate_touch'; corner: 0 | 1 | 2 | 3 }
  | { type: 'next' }
