// A plain live picture of the state message, for the vision lane: what the server says is
// on the mat, drawn straight from /ws. It reads the new contract (server/tacto/contract.py)
// and nothing from src/, so it works whatever state the product UI is in. Needs `make dev`
// or `make mock` on port 8000.

import { useEffect, useRef, useState } from 'react'

type Dot = [number, number]

interface Piece {
  id: string
  type: 'wire' | 'battery' | 'bulb' | 'resistor' | 'switch'
  a: Dot
  b: Dot
  closed: boolean | null
  current: number
  brightness: number | null
  shorted: boolean
}

interface State {
  seq: number
  t: number
  source: string
  mat_visible: boolean
  grid: { cols: number; rows: number }
  pieces: Piece[]
  circuit: { status: string; voltage: number; total_current: number; shorted_path: string[] }
  touch: {
    present: boolean
    x: number
    y: number
    piece_id: string | null
    pulse_hz: number
    buzz: boolean
  }
  lesson: {
    step_index: number
    step_count: number
    prompt: string
    step_done: boolean
    lesson_done: boolean
  }
}

const PITCH = 100 // drawing units between neighbouring dots
const MARGIN = 60
const RETRY_MS = 1000
// The printed pieces' own colours (kit/pieces.yaml), so the picture looks like the desk.
const COLOUR = {
  wire: 'rgb(30,70,210)',
  bulb: 'rgb(255,225,0)',
  resistor: 'rgb(215,0,170)',
  closed: 'rgb(20,165,50)',
  open: 'rgb(0,175,180)',
  plus: 'rgb(220,20,20)',
  minus: 'rgb(20,20,20)',
}

function at(dot: Dot): [number, number] {
  return [MARGIN + dot[0] * PITCH, MARGIN + dot[1] * PITCH]
}

function PieceShape({ piece, touched }: { piece: Piece; touched: boolean }) {
  const [ax, ay] = at(piece.a)
  const [bx, by] = at(piece.b)
  const [mx, my] = [(ax + bx) / 2, (ay + by) / 2]
  const angle = (Math.atan2(by - ay, bx - ax) * 180) / Math.PI
  const fill =
    piece.type === 'switch'
      ? piece.closed
        ? COLOUR.closed
        : COLOUR.open
      : piece.type === 'battery'
        ? COLOUR.plus
        : COLOUR[piece.type]
  const milliamps = Math.abs(piece.current) * 1000
  return (
    // Drawn lying from a (left) to b (right), then turned to where the piece really is.
    <g transform={`translate(${mx} ${my}) rotate(${angle})`}>
      {piece.type === 'bulb' && (piece.brightness ?? 0) > 0 && (
        <circle r={30 + 40 * (piece.brightness ?? 0)} fill="rgba(255,225,0,0.35)" />
      )}
      <rect
        x={-44}
        y={-16}
        width={88}
        height={32}
        rx={12}
        fill={fill}
        stroke={piece.shorted ? 'red' : touched ? 'white' : 'none'}
        strokeWidth={piece.shorted ? 6 : 4}
      />
      {piece.type === 'battery' && (
        <>
          <rect x={0} y={-16} width={44} height={32} rx={12} fill={COLOUR.minus} />
          <text x={-22} y={7} textAnchor="middle" fill="white" fontSize={22} fontWeight="bold">
            +
          </text>
          <text x={22} y={7} textAnchor="middle" fill="white" fontSize={22} fontWeight="bold">
            −
          </text>
        </>
      )}
      {piece.type === 'switch' && (
        <line
          x1={-18}
          y1={0}
          x2={18}
          y2={piece.closed ? 0 : -14}
          stroke="black"
          strokeWidth={4}
          strokeLinecap="round"
        />
      )}
      {piece.type === 'bulb' && <circle r={11} fill="none" stroke="black" strokeWidth={3} />}
      {piece.type === 'resistor' && (
        <polyline
          points="-20,0 -12,-8 -4,8 4,-8 12,8 20,0"
          fill="none"
          stroke="white"
          strokeWidth={3}
        />
      )}
      {milliamps > 0.05 && (
        // Kept upright whichever way the piece lies.
        <text
          y={-24}
          textAnchor="middle"
          fill="white"
          fontSize={15}
          transform={`rotate(${-angle})`}
        >
          {milliamps.toFixed(0)} mA
        </text>
      )}
    </g>
  )
}

export default function StatePanel() {
  const [state, setState] = useState<State | null>(null)
  const [connected, setConnected] = useState(false)
  const [rate, setRate] = useState(0)
  const socket = useRef<WebSocket | null>(null)
  const count = useRef(0)

  useEffect(() => {
    let closed = false
    let retry: ReturnType<typeof setTimeout> | undefined
    const connect = () => {
      const ws = new WebSocket(
        `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`,
      )
      socket.current = ws
      ws.onopen = () => setConnected(true)
      ws.onmessage = (event) => {
        count.current += 1
        setState(JSON.parse(String(event.data)) as State)
      }
      ws.onclose = () => {
        setConnected(false)
        if (!closed) retry = setTimeout(connect, RETRY_MS)
      }
    }
    connect()
    const meter = setInterval(() => {
      setRate(count.current)
      count.current = 0
    }, 1000)
    return () => {
      closed = true
      clearTimeout(retry)
      clearInterval(meter)
      socket.current?.close()
    }
  }, [])

  const setVolts = (volts: number) =>
    socket.current?.send(JSON.stringify({ type: 'set_voltage', volts }))

  if (!state) {
    return (
      <main className="mx-auto max-w-6xl p-8">
        <p className="opacity-70">
          {connected
            ? 'Connected, waiting for the first state…'
            : 'No server on port 8000. Run make dev (camera) or make mock.'}
        </p>
      </main>
    )
  }

  const width = 2 * MARGIN + (state.grid.cols - 1) * PITCH
  const height = 2 * MARGIN + (state.grid.rows - 1) * PITCH
  const status = state.circuit.status
  const statusColour =
    status === 'working'
      ? 'text-emerald-400'
      : status === 'shorted'
        ? 'text-rose-400'
        : 'text-amber-300'

  return (
    <main className="mx-auto grid max-w-7xl gap-6 p-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className={`w-full rounded-xl bg-white/5 ${state.mat_visible ? '' : 'opacity-40'}`}
      >
        {Array.from({ length: state.grid.rows }, (_, row) =>
          Array.from({ length: state.grid.cols }, (_, col) => (
            <circle
              key={`${col},${row}`}
              cx={at([col, row])[0]}
              cy={at([col, row])[1]}
              r={5}
              fill="#888"
            />
          )),
        )}
        {state.pieces.map((piece) => (
          <PieceShape key={piece.id} piece={piece} touched={piece.id === state.touch.piece_id} />
        ))}
        {state.touch.present && (
          <circle
            cx={MARGIN + state.touch.x * (state.grid.cols - 1) * PITCH}
            cy={MARGIN + state.touch.y * (state.grid.rows - 1) * PITCH}
            r={16}
            fill="none"
            stroke="white"
            strokeWidth={3}
          />
        )}
      </svg>

      <aside className="flex flex-col gap-4">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-xl bg-white/5 p-4">
          <dt className="opacity-60">Server</dt>
          <dd className={connected ? '' : 'text-rose-400'}>
            {connected ? `${state.source}, ${rate} states/s` : 'disconnected'}
          </dd>
          <dt className="opacity-60">Mat</dt>
          <dd className={state.mat_visible ? 'text-emerald-400' : 'text-amber-300'}>
            {state.mat_visible ? 'visible' : 'not found: pieces held'}
          </dd>
          <dt className="opacity-60">Circuit</dt>
          <dd className={`font-semibold ${statusColour}`}>{status}</dd>
          <dt className="opacity-60">Battery</dt>
          <dd>{state.circuit.voltage.toFixed(1)} V</dd>
          <dt className="opacity-60">Current</dt>
          <dd>{(state.circuit.total_current * 1000).toFixed(0)} mA</dd>
          <dt className="opacity-60">Pieces</dt>
          <dd>{state.pieces.length}</dd>
          <dt className="opacity-60">Finger</dt>
          <dd>
            {state.touch.present
              ? state.touch.piece_id
                ? `on ${state.touch.piece_id}, ${state.touch.buzz ? 'buzz' : `${state.touch.pulse_hz} Hz`}`
                : 'over the mat'
              : 'none'}
          </dd>
        </dl>

        <label className="flex flex-col gap-2 rounded-xl bg-white/5 p-4">
          <span className="opacity-60">Voltage (what the scroll wheel sends)</span>
          <input
            type="range"
            min={0}
            max={9}
            step={0.5}
            value={state.circuit.voltage}
            onChange={(event) => setVolts(Number(event.target.value))}
          />
        </label>

        <div className="rounded-xl bg-white/5 p-4">
          <p className="opacity-60">
            Lesson step {state.lesson.step_index + 1} of {state.lesson.step_count}
            {state.lesson.lesson_done ? ' (lesson done)' : state.lesson.step_done ? ' (done)' : ''}
          </p>
          <p className="mt-2">{state.lesson.prompt || '–'}</p>
        </div>

        <ul className="rounded-xl bg-white/5 p-4 font-mono text-sm">
          {state.pieces.map((piece) => (
            <li key={piece.id}>
              {piece.id} {piece.type}
              {piece.type === 'switch' ? (piece.closed ? ' closed' : ' open') : ''}
              {piece.type === 'battery' ? ` + at ${piece.a.join(',')}` : ''}
              {piece.shorted ? ' SHORTED' : ''}
            </li>
          ))}
        </ul>
      </aside>
    </main>
  )
}
