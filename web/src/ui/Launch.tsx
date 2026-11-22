// The first screen: a drawn workbench with a circuit board on the mat. Clicking the board
// opens the lab, and clicking the sticky note on the wall opens the gallery. Nothing here
// talks to the server.

import pcb from '../assets/Pcb.png'
import stickyNote from '../assets/StickyNote.png'
import workspace from '../assets/WorkspaceNoStickyNote.png'

// Workspace.png is 3593 x 1620. The board is placed in percentages of that picture so it
// stays on the blue desk mat at any window size. If the picture changes, update both.
const SCENE_ASPECT = 3593 / 1620
const BOARD = { centreX: 52.5, centreY: 81.5, width: 27 } // percent of the scene
// Where the sticky note hung in the picture before it was taken out and made a button. It is the
// note's own picture put back in the same place.
const NOTE = { centreX: 81.75, centreY: 21.7, width: 15.1 } // percent of the scene

export function Launch({
  onOpen,
  onOpenGallery,
}: {
  onOpen: () => void
  onOpenGallery: () => void
}) {
  return (
    <div className="flex h-full items-center justify-center overflow-hidden bg-[#dcefb0]">
      <div
        className="relative"
        style={{
          // Covers the whole window, keeping the picture's shape: a window narrower than the
          // picture loses a little of its left and right edges, never the middle.
          width: `max(100vw, ${100 * SCENE_ASPECT}vh)`,
          flexShrink: 0,
          aspectRatio: `${SCENE_ASPECT}`,
        }}
      >
        <img
          src={workspace}
          alt=""
          className="absolute inset-0 h-full w-full select-none"
          draggable={false}
        />

        <h1 className="absolute top-[6%] left-1/2 -translate-x-1/2 text-center text-[clamp(2rem,6vw,5rem)] font-bold tracking-tight text-[#1f2a14]">
          Tacto
        </h1>

        <button
          type="button"
          onClick={onOpen}
          aria-label="Open the circuit lab"
          className="group absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-xl focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-yellow-300"
          style={{
            left: `${BOARD.centreX}%`,
            top: `${BOARD.centreY}%`,
            width: `${BOARD.width}%`,
          }}
        >
          <img
            src={pcb}
            alt=""
            draggable={false}
            className="w-full transition-transform duration-200 ease-out select-none group-hover:scale-110 group-focus-visible:scale-110 motion-reduce:transition-none"
          />
        </button>

        <button
          type="button"
          onClick={onOpenGallery}
          aria-label="Open the gallery"
          className="group absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-xl focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-yellow-300"
          style={{
            left: `${NOTE.centreX}%`,
            top: `${NOTE.centreY}%`,
            width: `${NOTE.width}%`,
          }}
        >
          <img
            src={stickyNote}
            alt=""
            draggable={false}
            className="w-full transition-transform duration-200 ease-out select-none group-hover:scale-110 group-hover:-rotate-3 group-focus-visible:scale-110 motion-reduce:transition-none"
          />
          {/* Written on the note, tilted with it. */}
          <span className="pointer-events-none absolute top-[53%] left-[50%] w-[62%] -translate-x-1/2 -translate-y-1/2 rotate-[15deg] text-center text-[clamp(0.8rem,2vw,2rem)] leading-tight font-bold text-[#1f2a14]">
            Gallery
          </span>
        </button>
      </div>
    </div>
  )
}
