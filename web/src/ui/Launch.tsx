// The first screen: a drawn workbench with a circuit board on the mat. Clicking the circuit
// board opens the bench to build freely (Tinker; the Lab button there starts the lesson), and
// the sticky note on the wall opens the gallery. Nothing here talks to the server: the mode is
// handed to the lab when it connects (useTacto.ts).

import logo from '../assets/Logo.png'
import pcb from '../assets/Pcb.png'
import stickyNote from '../assets/StickyNote.png'
import workspace from '../assets/HomeBackground.png'

// HomeBackground.png is 3593 x 1620. The board is placed in percentages of that picture so it
// stays on the blue desk mat at any window size. If the picture changes, update both.
const SCENE_ASPECT = 3593 / 1620
const BOARD = { centreX: 52.5, centreY: 81.5, width: 27 } // percent of the scene
// The clipboard's paper on the wall (percent of the scene): "Tacto" is written on it.
const PAPER = { centreX: 51.4, centreY: 29.8, width: 26.5, height: 22.5 }
// The edition stamp, on the wall under the right end of the clipboard (percent of the scene).
const EDITION = { centreX: 74, centreY: 50 }
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
    <div className="relative flex h-full items-center justify-center overflow-hidden bg-[#dcefb0]">
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

        {/* Written on the clipboard's paper: the logo and the name, and what it is, sized
            with the scene (container units) so it stays on the paper at any window size. */}
        <div
          className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-[6%] [container-type:size]"
          style={{
            left: `${PAPER.centreX}%`,
            top: `${PAPER.centreY}%`,
            width: `${PAPER.width}%`,
            height: `${PAPER.height}%`,
          }}
        >
          <div className="flex items-center gap-[4cqw]">
            <img
              src={logo}
              alt="Tacto logo"
              draggable={false}
              className="h-[34cqh] w-auto -rotate-3 select-none"
            />
            <h1 className="m-0 font-['Patrick_Hand'] text-[42cqh] leading-none text-[#1f2a14]">
              Tacto
            </h1>
          </div>
          <p className="m-0 -rotate-1 font-['Patrick_Hand'] text-[13cqh] leading-none text-[#6b4a2b]">
            science within reach
          </p>
        </div>
        {/* Stamped on the green wall beside the clipboard, like an edition mark: this kit is
            the circuits one. */}
        <span
          className="absolute -translate-x-1/2 -translate-y-1/2 rotate-[-14deg] rounded-[0.6vw] border-[0.35vw] border-[#c2412d] bg-[#fff6ea]/70 px-[1.1vw] pt-[0.5vw] pb-[0.25vw] font-['Patrick_Hand'] text-[clamp(1.3rem,3vw,3.2rem)] leading-none tracking-wide whitespace-nowrap text-[#c2412d] uppercase shadow-sm select-none"
          style={{ left: `${EDITION.centreX}%`, top: `${EDITION.centreY}%` }}
        >
          Circuitry edition
        </span>
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

      {/* For the people running the demo: the setup check and the other tools. Small and in
          the corner, so a judge's eye goes to the workbench. */}
      <a
        href="/devtools/#setup"
        title="Dev tools: the setup check, the camera bench, the haptics test"
        className="absolute right-3 bottom-3 z-10 flex items-center gap-1.5 rounded-full bg-[#1f2a14]/70 px-3 py-1 font-['Patrick_Hand'] text-sm text-[#f4f1e6] shadow-md backdrop-blur-sm transition hover:bg-[#1f2a14] focus-visible:outline-4 focus-visible:outline-yellow-300"
      >
        <svg
          viewBox="0 0 24 24"
          aria-hidden="true"
          className="h-3.5 w-3.5 fill-none stroke-current"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z" />
        </svg>
        Dev tools
      </a>
    </div>
  )
}
