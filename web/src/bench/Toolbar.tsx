import multimeterUrl from '../assets/Multimeter.png'

interface ToolbarProps {
  /** The multimeter is picked up: it is the pointer over the mat. */
  probing: boolean
  onToggle: () => void
  /** Save a picture of the circuit. */
  onScreenshot: () => void
}

/** Its width. The mat is drawn to the right of it, so no tool ever covers the circuit. */
export const TOOLBAR_WIDTH_CLASS = 'w-40'

/**
 * The tool bar: a tall block down the left edge of the mat, with room for more tools below the
 * multimeter. Click a tool to pick it up and again to let go. Big and filled when in hand,
 * because the room has to see which tool it is.
 */
export function Toolbar({ probing, onToggle, onScreenshot }: ToolbarProps) {
  return (
    <nav
      aria-label="Tools"
      className={`absolute inset-y-0 left-0 z-10 flex flex-col gap-3 bg-emerald-950 p-4 ${TOOLBAR_WIDTH_CLASS}`}
    >
      <button
        type="button"
        aria-pressed={probing}
        onClick={onToggle}
        className={`flex w-full cursor-pointer flex-col items-center gap-1 rounded-xl border-4 px-2 py-3 text-lg font-semibold focus-visible:outline-4 focus-visible:outline-sky-300 ${
          // Filled and outlined as well as coloured: the state is not carried by colour alone.
          probing
            ? 'border-amber-300 bg-amber-300 text-stone-900'
            : 'border-stone-100/40 bg-transparent text-stone-100 hover:border-stone-100'
        }`}
      >
        <img src={multimeterUrl} alt="" className="h-20 object-contain" />
        Multimeter
      </button>
      <button
        type="button"
        onClick={onScreenshot}
        className="flex w-full cursor-pointer flex-col items-center gap-1 rounded-xl border-4 border-stone-100/40 px-2 py-3 text-lg font-semibold text-stone-100 hover:border-stone-100 focus-visible:outline-4 focus-visible:outline-sky-300"
      >
        <svg viewBox="0 0 64 48" className="h-20 w-20" aria-hidden="true">
          <path
            d="M8 12h12l4-6h16l4 6h12a4 4 0 0 1 4 4v26a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V16a4 4 0 0 1 4-4Z"
            className="fill-none stroke-stone-100"
            strokeWidth={4}
            strokeLinejoin="round"
          />
          <circle cx={32} cy={28} r={9} className="fill-none stroke-stone-100" strokeWidth={4} />
        </svg>
        Screenshot
      </button>
    </nav>
  )
}
