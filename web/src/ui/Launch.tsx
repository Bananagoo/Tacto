// The first screen: a drawn workbench with a circuit board on the mat. Clicking the circuit
// board opens the bench to build freely (Tinker; the Lab button there starts the lesson), and
// the sticky note on the wall opens the gallery. Nothing here talks to the server: the mode is
// handed to the lab when it connects (useTacto.ts).

import logo from '../assets/Logo.png'
import pcb from '../assets/Pcb.png'
import stickyNote from '../assets/StickyNote.png'
import workspace from '../assets/WorkspaceNoStickyNote.png'

// Workspace.png is 3593 x 1620. The board is placed in percentages of that picture so it
// stays on the blue desk mat at any window size. If the picture changes, update both.
const SCENE_ASPECT = 3593 / 1620
const BOARD = { centreX: 52.5, centreY: 81.5, width: 27 } // percent of the scene
// The word "Tacto" is centred over the circuit board; the small logo sits beside the word.
const TITLE = { centreX: BOARD.centreX, centreY: 10 } // percent of the scene
// Where the sticky note hung in the picture before it was taken out and made a button. It is the
// note's own picture put back in the same place.
const NOTE = { centreX: 81.75, centreY: 21.7, width: 15.1 } // percent of the scene

export function Launch({
  onOpen,
  onOpenGallery,
}: {
  onOpen: (mode: 'tinker' | 'lab') => void
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

        {/* The word is centred over the board; the small logo hangs off its left. */}
        <div
          className="absolute -translate-x-1/2 -translate-y-1/2"
          style={{ left: `${TITLE.centreX}%`, top: `${TITLE.centreY}%` }}
        >
          <h1 className="m-0 text-center font-['Patrick_Hand'] text-[clamp(2.4rem,7.5vw,6.2rem)] leading-none text-[#1f2a14]">
            Tacto
          </h1>
          <img
            src={logo}
            alt="Tacto logo"
            draggable={false}
            className="absolute top-1/2 right-full mr-[clamp(0.5rem,1.2vw,1.2rem)] h-[clamp(2.5rem,6.5vw,5.5rem)] w-auto -translate-y-1/2 select-none"
          />
        </div>
        {/* The circuit board grows under the pointer and opens the bench to build freely. */}
        <button
          type="button"
          onClick={() => onOpen('tinker')}
          aria-label="Open the circuit board to build freely"
          title="Build freely"
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
          {/* The note and its writing grow and tilt together under the pointer. */}
          <div className="relative transition-transform duration-200 ease-out group-hover:scale-110 group-hover:-rotate-3 group-focus-visible:scale-110 motion-reduce:transition-none">
            <img src={stickyNote} alt="" draggable={false} className="w-full select-none" />
            {/* Written on the note: centred on its yellow paper (47% across, 50% down, clear
                of the pin and the folded corner) and turned with it, about 15 degrees. */}
            <span className="pointer-events-none absolute top-[50%] left-[47%] w-[62%] -translate-x-1/2 -translate-y-1/2 rotate-[15deg] text-center font-['Patrick_Hand'] text-[clamp(1rem,2.6vw,2.6rem)] leading-tight text-[#1f2a14]">
              Gallery
            </span>
          </div>
        </button>
      </div>
    </div>
  )
}
