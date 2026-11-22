// Two things live here.
//
// 1. The wire contract: a mirror of server/tacto/contract.py, which is the source of
//    truth (JSON schema in contract/). `ServerState` is the one message the server sends;
//    the page sends SetVoltage, SetMode, RestartLesson, ContinueLesson,
//    AnswerReflection or ReflectionHeard. Change both sides together.
//
// 2. The page's own picture of that state (`State`, `Part`, `Wire`, `Probe`): the shapes
//    the bench, the multimeter and the haptics were built on. `fromServer.ts` turns a
//    ServerState into one, and is the only place that knows both.

export type Dot = [col: number, row: number]

// ---------- the wire contract: server -> web ----------

export type PieceType = 'wire' | 'battery' | 'bulb' | 'resistor' | 'switch'
export type ServerCircuitStatus = 'working' | 'open' | 'shorted'
export type Mode = 'tinker' | 'lab'

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
  /** Ohms: 0 for a wire and a closed switch; null for a battery and an open switch. */
  resistance: number | null
  /** On the shorted path. */
  shorted: boolean
}

export interface ServerState {
  type: 'state'
  version: number
  seq: number
  t: number
  source: 'camera' | 'replay' | 'manual'
  mode: Mode
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
    reflection: string | null
    /** The five below are set only while an adaptive reflection runs (contract/README.md). */
    reflection_level: number | null
    reflection_status: ReflectionStatus | null
    reflection_line: string | null
    reflection_line_id: number
    reflection_transcript: string | null
    /** Where `reflection_line` can be fetched as speech, or null when it is only shown. */
    reflection_audio: string | null
  }
}

export type ReflectionStatus = 'asking' | 'listening' | 'thinking' | 'resolved' | 'exit'

// ---------- the wire contract: web -> server ----------

export const MAX_VOLTS = 9

export interface SetVoltage {
  type: 'set_voltage'
  volts: number
}

export interface RestartLesson {
  type: 'restart_lesson'
}

export interface SetMode {
  type: 'set_mode'
  mode: Mode
}

export interface ContinueLesson {
  type: 'continue_lesson'
  step_id: string
}

export interface AnswerReflection {
  type: 'answer_reflection'
  step_id: string
  text: string
  /** The reflection_line_id being answered, so a late answer is dropped, not misplaced. */
  line_id?: number
}

/** A line's audio finished playing, or could not be played. */
export interface ReflectionHeard {
  type: 'reflection_heard'
  step_id: string
  line_id: number
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
  /** Ohms; null for a battery or a switch. */
  resistance: number | null
  /** On the shorted path. */
  shorted: boolean
}

export interface Wire {
  /** The piece's id on the server: its segment. */
  id: string
  a: Dot
  b: Dot
  current: number
  overloaded: boolean
  /** Ohms: 0, a plain wire. */
  resistance: number
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
  step_id: string
  step_index: number
  step_count: number
  prompt: string
  step_done: boolean
  lesson_done: boolean
  reflection: string | null
  /** Null unless an adaptive reflection is running: then what the lab is doing ... */
  reflectionStatus: ReflectionStatus | null
  /** ... what it is saying now (a question, a confirmation, or the idea stated) ... */
  reflectionLine: string | null
  /** ... which changes with step_id and this id, the same line said again included ... */
  reflectionLineId: number
  /** ... and the learner's last answer. */
  reflectionTranscript: string | null
  /** Where the line can be fetched as speech, or null when it is only shown. */
  reflectionAudio: string | null
}

export interface State {
  type: 'state'
  t: number
  source: 'camera' | 'replay' | 'manual'
  mode: Mode
  mat_visible: boolean
  circuit: Circuit
  probe: Probe
  lesson: Lesson
  tutor: Tutor
  learner: Partial<Record<Concept, Mastery>>
}

export type ClientMessage =
  | SetVoltage
  | RestartLesson
  | SetMode
  | ContinueLesson
  | AnswerReflection
  | ReflectionHeard
  | ParkedClientMessage

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
