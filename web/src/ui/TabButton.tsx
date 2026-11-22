import type { ReactNode } from 'react'

// The tab pictures are all 357 x 112: a hand-drawn arrow, its point the right-hand 18%. The
// words sit in the flat part, clear of the point.
const TAB_ASPECT = 357 / 112

/**
 * A top-bar button drawn as a paper tab in its own colour: dimmed until it is the one open,
 * full colour when open or under the pointer. The words are in the notebook's handwriting.
 */
export function TabButton({
  art,
  chosen,
  onClick,
  disabled,
  title,
  pressed,
  label,
  long,
  besidePicture,
  children,
}: {
  /** The coloured tab, shown when chosen. */
  art: string
  chosen: boolean
  onClick?: () => void
  disabled?: boolean
  title?: string
  /** For a toggle (Tinker, Lab): its aria-pressed. */
  pressed?: boolean
  /** The words for a screen reader, when the visible ones are not enough. */
  label?: string
  /** Longer words ("Connect mouse"): written a size smaller to stay clear of the edges. */
  long?: boolean
  /** The coloured tab has a picture at its left (Home's house): the words sit to its right. */
  besidePicture?: boolean
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-pressed={pressed}
      aria-label={label}
      style={{ aspectRatio: TAB_ASPECT }}
      className="group relative h-12 shrink-0 cursor-pointer select-none focus-visible:outline-none disabled:cursor-default disabled:opacity-40"
    >
      {/* Its own colour always; dimmed until it is the one open, full under the pointer. */}
      <img
        src={art}
        alt=""
        draggable={false}
        className={`absolute inset-0 h-full w-full transition-[opacity,filter,transform] duration-200 motion-reduce:transition-none ${
          chosen
            ? 'opacity-100'
            : 'opacity-55 saturate-75 group-hover:opacity-100 group-hover:saturate-100 group-focus-visible:opacity-100 group-disabled:opacity-55'
        } group-active:scale-95`}
      />
      <span
        className={`absolute inset-y-0 ${besidePicture ? 'left-[30%] right-[18%]' : 'left-[6%] right-[20%]'} flex items-center justify-center gap-1.5 pt-0.5 font-['Patrick_Hand'] ${long ? 'text-[1.05rem]' : 'text-[1.35rem]'} leading-none whitespace-nowrap text-[#1f2a14] transition-opacity ${
          chosen ? '' : 'opacity-75 group-hover:opacity-100'
        } group-focus-visible:underline`}
      >
        {children}
      </span>
    </button>
  )
}
