// The server's state message as the page's own picture of it. The only file that knows
// both shapes (see contract.ts): everything the page draws or plays reads the result.
//
// Nothing here is worked out: every number is the server's. Pieces are only sorted into
// parts and wires, and names are changed.

import type { CircuitStatus, Part, ServerPiece, ServerState, State, Wire } from './contract'

const STATUS: Record<ServerState['circuit']['status'], CircuitStatus> = {
  working: 'closed',
  open: 'open',
  shorted: 'short',
}

function toPart(piece: ServerPiece & { type: Part['kind'] }): Part {
  return {
    id: piece.id,
    kind: piece.type,
    a: piece.a,
    b: piece.b,
    closed: piece.closed,
    current: piece.current,
    voltage: piece.voltage,
    brightness: piece.brightness ?? 0,
  }
}

function toWire(piece: ServerPiece): Wire {
  return {
    id: piece.id,
    a: piece.a,
    b: piece.b,
    current: piece.current,
    overloaded: piece.shorted,
  }
}

export function fromServer(server: ServerState): State {
  const parts: Part[] = []
  const wires: Wire[] = []
  for (const piece of server.pieces) {
    if (piece.type === 'wire') wires.push(toWire(piece))
    else parts.push(toPart({ ...piece, type: piece.type }))
  }
  const touched = server.pieces.find((piece) => piece.id === server.touch.piece_id)
  return {
    type: 'state',
    t: server.t,
    source: server.source,
    mat_visible: server.mat_visible,
    circuit: {
      // An empty mat is "open" to the server; the page has its own word for it.
      status: server.pieces.length === 0 ? 'empty' : STATUS[server.circuit.status],
      source_voltage: server.circuit.voltage,
      total_current: server.circuit.total_current,
      parts,
      wires,
    },
    probe: {
      present: server.touch.present,
      x: server.touch.x,
      y: server.touch.y,
      on: server.touch.piece_id,
      current: touched?.current ?? 0,
      pulse_hz: server.touch.pulse_hz,
      strength: server.touch.strength,
      buzz: server.touch.buzz,
    },
    lesson: {
      step_index: server.lesson.step_index,
      step_count: server.lesson.step_count,
      prompt: server.lesson.prompt,
      step_done: server.lesson.step_done,
      lesson_done: server.lesson.lesson_done,
    },
    // Parked: filled so the components kept in ui/ still have something to read.
    tutor: {
      lesson_id: server.lesson.lesson_id,
      challenge_id: server.lesson.step_id,
      step_index: server.lesson.step_index,
      step_count: server.lesson.step_count,
      phase: server.lesson.lesson_done ? 'done' : 'build',
      prompt: server.lesson.prompt,
      choices: [],
      correct: null,
      feedback: '',
      hint: '',
      audio_url: null,
      zone: 'productive',
      score: 0,
    },
    learner: {},
  }
}
