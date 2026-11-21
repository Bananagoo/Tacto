import type { MouseEvent } from 'react'
import type { Dot, MatView } from './api'

const PITCH = 60
const MARGIN = 40

const at = ([col, row]: Dot) => ({ x: MARGIN + col * PITCH, y: MARGIN + row * PITCH })

/**
 * A small map of the mat. Click anywhere to put the fingertip there: it stands in for the
 * hand the camera would see. Positions are 0..1 from the first dot to the last, as the
 * server expects.
 */
export default function MatPad({
  mat,
  onTouch,
}: {
  mat: MatView
  onTouch: (x: number, y: number) => void
}) {
  const { layout } = mat
  const width = (layout.cols - 1) * PITCH
  const height = (layout.rows - 1) * PITCH

  const touch = (event: MouseEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    const scale = (width + 2 * MARGIN) / box.width
    const x = ((event.clientX - box.left) * scale - MARGIN) / width
    const y = ((event.clientY - box.top) * scale - MARGIN) / height
    onTouch(Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y)))
  }

  const line = (a: Dot, b: Dot, key: string, className: string, dashed = false) => (
    <line
      key={key}
      x1={at(a).x}
      y1={at(a).y}
      x2={at(b).x}
      y2={at(b).y}
      className={className}
      strokeWidth={6}
      strokeLinecap="round"
      strokeDasharray={dashed ? '4 10' : undefined}
    />
  )

  return (
    <svg
      viewBox={`0 0 ${width + 2 * MARGIN} ${height + 2 * MARGIN}`}
      className="w-full cursor-crosshair rounded-lg bg-black/40"
      onClick={touch}
    >
      {layout.wires.map((wire, i) => line(wire.a, wire.b, `w${i}`, 'stroke-white/60'))}
      {layout.parts.map((part) => line(part.a, part.b, part.id, 'stroke-amber-300'))}
      {layout.drawables.map((drawable) =>
        mat.drawn.includes(drawable.id)
          ? line(drawable.a, drawable.b, drawable.id, 'stroke-sky-400')
          : line(drawable.a, drawable.b, drawable.id, 'stroke-sky-400/50', true),
      )}
      {layout.slots.map((slot) => {
        const content = mat.slots[slot.id] ?? 'empty'
        if (content === 'empty') return line(slot.a, slot.b, slot.id, 'stroke-white/25', true)
        return line(
          slot.a,
          slot.b,
          slot.id,
          content === 'wire' ? 'stroke-white/60' : 'stroke-amber-300',
        )
      })}
      {mat.fingertip && (
        <circle
          cx={MARGIN + mat.fingertip.x * width}
          cy={MARGIN + mat.fingertip.y * height}
          r={12}
          className="fill-none stroke-rose-400"
          strokeWidth={4}
        />
      )}
    </svg>
  )
}
