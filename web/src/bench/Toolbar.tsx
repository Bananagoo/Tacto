import { useState } from 'react'
import cameraUrl from '../assets/camera.png'
import eraserUrl from '../assets/eraser.png'
import markerUrl from '../assets/marker.png'
import multimeterUrl from '../assets/Multimeter.png'
import { ERASER_SIZES, MARKER_COLORS } from './markers'

/** What the pointer is doing over the mat: nothing, reading as the multimeter, drawing, or erasing. */
export type Tool = 'none' | 'multimeter' | 'marker' | 'eraser'

interface ToolbarProps {
  tool: Tool
  /** Pick a tool up, or put it down if it is already in hand. */
  onPick: (tool: 'multimeter' | 'marker' | 'eraser') => void
  markerColor: string
  onMarkerColor: (color: string) => void
  onClearMarker: () => void
  eraserRadius: number
  onEraserRadius: (radius: number) => void
  /** Save a dated picture of the circuit to the gallery. Resolves once it is saved. */
  onScreenshot: () => Promise<void>
  /** Leave the lab for the home page. */
  onHome: () => void
}

/** Its width. The mat is drawn to the right of it, so no tool ever covers the circuit. */
export const TOOLBAR_WIDTH_CLASS = 'w-40'

const TOOL_BUTTON =
  'flex w-full cursor-pointer flex-col items-center gap-1 rounded-xl border-4 px-2 py-3 text-lg font-semibold focus-visible:outline-4 focus-visible:outline-sky-300'
// Filled and outlined as well as coloured: the tool in hand is not carried by colour alone.
const IN_HAND = 'border-amber-300 bg-amber-300 text-stone-900'
const PUT_DOWN = 'border-stone-100/40 bg-transparent text-stone-100 hover:border-stone-100'

/**
 * The tool bar: a tall block down the left edge of the mat, with room for more tools below the
 * multimeter. Click a tool to pick it up and again to let go. Big and filled when in hand,
 * because the room has to see which tool it is.
 */
export function Toolbar({
  tool,
  onPick,
  markerColor,
  onMarkerColor,
  onClearMarker,
  eraserRadius,
  onEraserRadius,
  onScreenshot,
  onHome,
}: ToolbarProps) {
  // "Saved" for a moment after a screenshot, "Could not save" if it failed. Words, not colour.
  const [shotNote, setShotNote] = useState<'' | 'Saved' | 'Could not save'>('')
  const takeShot = () => {
    onScreenshot().then(
      () => setShotNote('Saved'),
      (error: unknown) => {
        console.error('bench:', error)
        setShotNote('Could not save')
      },
    )
    setTimeout(() => setShotNote(''), 2500)
  }
  return (
    <nav
      aria-label="Tools"
      className={`absolute inset-y-0 left-0 z-10 flex flex-col gap-3 bg-emerald-950 p-4 ${TOOLBAR_WIDTH_CLASS}`}
    >
      <button
        type="button"
        aria-pressed={tool === 'multimeter'}
        onClick={() => onPick('multimeter')}
        className={`${TOOL_BUTTON} ${tool === 'multimeter' ? IN_HAND : PUT_DOWN}`}
      >
        <img src={multimeterUrl} alt="" className="h-20 object-contain" />
        Multimeter
      </button>
      <button
        type="button"
        aria-pressed={tool === 'marker'}
        onClick={() => onPick('marker')}
        className={`${TOOL_BUTTON} ${tool === 'marker' ? IN_HAND : PUT_DOWN}`}
      >
        <img src={markerUrl} alt="" className="h-20 object-contain" />
        Marker
      </button>
      <button
        type="button"
        aria-pressed={tool === 'eraser'}
        onClick={() => onPick('eraser')}
        className={`${TOOL_BUTTON} ${tool === 'eraser' ? IN_HAND : PUT_DOWN}`}
      >
        <img src={eraserUrl} alt="" className="h-16 object-contain" />
        Eraser
      </button>
      {tool === 'eraser' && (
        <div className="flex items-end justify-center gap-3 rounded-xl bg-white/10 p-3">
          {ERASER_SIZES.map((size) => (
            <button
              key={size.name}
              type="button"
              aria-label={`${size.name} eraser`}
              aria-pressed={eraserRadius === size.radius}
              onClick={() => onEraserRadius(size.radius)}
              // Three rings in three sizes, as big as the eraser's reach; a thick ring marks the chosen one.
              style={{ width: size.radius * 0.75 + 8, height: size.radius * 0.75 + 8 }}
              className={`cursor-pointer rounded-full border-4 border-stone-100 focus-visible:outline-4 focus-visible:outline-sky-300 ${
                eraserRadius === size.radius ? 'bg-amber-300' : 'bg-transparent'
              }`}
            />
          ))}
        </div>
      )}
      {tool === 'marker' && (
        <div className="flex flex-col items-center gap-3 rounded-xl bg-white/10 p-3">
          <div className="grid grid-cols-2 gap-3">
            {MARKER_COLORS.map((ink) => (
              <button
                key={ink.value}
                type="button"
                aria-label={`${ink.name} ink`}
                aria-pressed={markerColor === ink.value}
                onClick={() => onMarkerColor(ink.value)}
                style={{ backgroundColor: ink.value }}
                // A thick ring on the chosen ink, so it is not told by colour alone.
                className={`h-9 w-9 cursor-pointer rounded-full border-2 border-stone-100/60 focus-visible:outline-4 focus-visible:outline-sky-300 ${
                  markerColor === ink.value ? 'ring-4 ring-amber-300' : ''
                }`}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={onClearMarker}
            className="w-full cursor-pointer rounded-lg border-2 border-stone-100/40 py-1 text-lg font-semibold text-stone-100 hover:border-stone-100 focus-visible:outline-4 focus-visible:outline-sky-300"
          >
            Clear
          </button>
        </div>
      )}
      <button
        type="button"
        onClick={takeShot}
        className="flex w-full cursor-pointer flex-col items-center gap-1 rounded-xl border-4 border-stone-100/40 px-2 py-3 text-lg font-semibold text-stone-100 hover:border-stone-100 focus-visible:outline-4 focus-visible:outline-sky-300"
      >
        <img src={cameraUrl} alt="" className="h-20 object-contain" />
        {shotNote || 'Screenshot'}
      </button>
      {/* At the bottom of the bar, apart from the tools: it leaves the lab, it is not a tool. */}
      <button type="button" onClick={onHome} className={`${TOOL_BUTTON} ${PUT_DOWN} mt-auto`}>
        <span className="text-5xl leading-none" aria-hidden="true">
          ←
        </span>
        Home
      </button>
    </nav>
  )
}
