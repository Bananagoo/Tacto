// The product's screen on a made-up, built-from-scratch circuit, with no server and no camera.
// For designing the screen while vision is still being built: pick a circuit, see how the
// bench draws it. The numbers are made up for looks (6 V, 10 ohm bulbs worked by hand below),
// they do not come from the solver.

import { useEffect, useState } from 'react'
import { Bench } from '../../src/bench/Bench'
import type { Circuit, Part, State, Wire } from '../../src/contract'
import { HapticsProvider } from '../../src/haptics/HapticsContext'
import { useTacto } from '../../src/useTacto'
import { CameraCorner } from '../../src/ui/CameraCorner'
import { StatusBar } from '../../src/ui/StatusBar'

const wire = (a: Wire['a'], b: Wire['b'], current: number, overloaded = false): Wire => ({
  a,
  b,
  current,
  overloaded,
})

function battery(current: number): Part {
  return {
    id: 'battery',
    kind: 'battery',
    a: [1, 2],
    b: [1, 3],
    closed: null,
    current,
    voltage: 6,
    brightness: 0,
  }
}

function bulb(id: string, a: Wire['a'], b: Wire['b'], current: number, brightness: number): Part {
  return { id, kind: 'bulb', a, b, closed: null, current, voltage: current * 10, brightness }
}

function circuit(partial: Partial<Circuit>): Circuit {
  return {
    status: 'closed',
    topology: 'single',
    source_voltage: 6,
    total_current: 0,
    parts: [],
    wires: [],
    ...partial,
  }
}

// Hand-worked: a 10 ohm bulb on 6 V carries 0.6 A and is at full brightness. Two in series
// are 20 ohm: 0.3 A, a quarter of the brightness. Two in parallel each carry 0.6 A, so the
// battery's wire carries 1.2 A.
const PRESETS: Record<string, Circuit> = {
  'Nothing placed yet': circuit({ status: 'empty', topology: 'none' }),
  'One bulb, loop closed': circuit({
    total_current: 0.6,
    parts: [battery(0.6), bulb('bulb_a', [3, 0], [5, 0], 0.6, 1)],
    wires: [
      wire([1, 2], [1, 0], 0.6),
      wire([1, 0], [3, 0], 0.6),
      wire([5, 0], [7, 0], 0.6),
      wire([7, 0], [7, 4], 0.6),
      wire([7, 4], [1, 4], 0.6),
      wire([1, 4], [1, 3], 0.6),
    ],
  }),
  'Loop with a gap (open)': circuit({
    status: 'open',
    topology: 'none',
    parts: [battery(0), bulb('bulb_a', [3, 0], [5, 0], 0, 0)],
    wires: [wire([1, 2], [1, 0], 0), wire([1, 0], [3, 0], 0), wire([5, 0], [7, 0], 0)],
  }),
  'Two bulbs in series': circuit({
    topology: 'series',
    total_current: 0.3,
    parts: [
      battery(0.3),
      bulb('bulb_a', [2, 0], [4, 0], 0.3, 0.25),
      bulb('bulb_b', [5, 0], [7, 0], 0.3, 0.25),
    ],
    wires: [
      wire([1, 2], [1, 0], 0.3),
      wire([1, 0], [2, 0], 0.3),
      wire([4, 0], [5, 0], 0.3),
      wire([7, 0], [7, 4], 0.3),
      wire([7, 4], [1, 4], 0.3),
      wire([1, 4], [1, 3], 0.3),
    ],
  }),
  'Two bulbs in parallel': circuit({
    topology: 'parallel',
    total_current: 1.2,
    parts: [
      battery(1.2),
      bulb('bulb_a', [3, 0], [5, 0], 0.6, 1),
      bulb('bulb_b', [3, 2], [5, 2], 0.6, 1),
    ],
    wires: [
      wire([1, 2], [1, 0], 1.2),
      wire([1, 0], [3, 0], 0.6),
      wire([1, 0], [1, 2], 0.6),
      wire([5, 0], [7, 0], 0.6),
      wire([5, 2], [7, 2], 0.6),
      wire([7, 0], [7, 4], 1.2),
      wire([7, 4], [1, 4], 1.2),
      wire([1, 4], [1, 3], 1.2),
    ],
  }),
  'A short circuit': circuit({
    status: 'short',
    topology: 'none',
    total_current: 0,
    parts: [battery(0), bulb('bulb_a', [3, 0], [5, 0], 0, 0)],
    wires: [
      wire([1, 2], [1, 0], 0, true),
      wire([1, 0], [3, 0], 0),
      wire([5, 0], [7, 0], 0),
      wire([1, 0], [7, 0], 0, true),
      wire([7, 0], [7, 4], 0, true),
      wire([7, 4], [1, 4], 0, true),
      wire([1, 4], [1, 3], 0, true),
    ],
  }),
}

const TOP_WIRE = { x: 0.25, y: 0, on: 'wire:1,0-3,0' }

function fakeState(circuitNow: Circuit, finger: boolean): State {
  const current =
    circuitNow.wires.find((w) => w.a[0] === 1 && w.b[0] === 3 && w.a[1] === 0)?.current ?? 0
  return {
    type: 'state',
    t: 0,
    source: 'mock',
    circuit: circuitNow,
    probe: {
      present: finger,
      x: TOP_WIRE.x,
      y: TOP_WIRE.y,
      on: finger ? TOP_WIRE.on : null,
      current,
      pulse_hz: current * 5,
      buzz: circuitNow.status === 'short',
    },
    // The tutor is not shown; the contract still carries it.
    tutor: {
      lesson_id: '',
      challenge_id: '',
      step_index: 0,
      step_count: 0,
      phase: 'build',
      prompt: '',
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

export default function ScratchPanel() {
  const [name, setName] = useState('One bulb, loop closed')
  const [finger, setFinger] = useState(true)

  // This page opens no socket, so it fills the store by hand and empties it on the way out.
  useEffect(() => {
    useTacto.setState({ connected: true, state: fakeState(PRESETS[name], finger) })
  }, [name, finger])
  useEffect(() => () => useTacto.setState({ connected: false, state: null }), [])

  return (
    <HapticsProvider>
      <main className="flex h-[calc(100vh-4rem)] flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center gap-2">
          {Object.keys(PRESETS).map((preset) => (
            <button
              key={preset}
              onClick={() => setName(preset)}
              className={`rounded px-3 py-1 ${preset === name ? 'bg-white/20' : 'bg-white/10 hover:bg-white/20'}`}
            >
              {preset}
            </button>
          ))}
          <label className="ml-4 flex items-center gap-2">
            <input type="checkbox" checked={finger} onChange={() => setFinger(!finger)} />
            Fingertip on the top wire
          </label>
          <span className="opacity-60">Made-up circuits, no server and no camera.</span>
        </div>
        <div className="grid min-h-0 flex-1">
          <Bench>
            <CameraCorner />
          </Bench>
        </div>
        <StatusBar />
      </main>
    </HapticsProvider>
  )
}
