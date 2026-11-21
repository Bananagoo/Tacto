// Layout only: the simulated circuit fills the screen with the camera picture over its corner,
// and the status bar runs along the bottom. Each piece reads what it needs from the store itself.
//
// The tutor and the concept map are out of the layout for now (Ananya Maheshwari, 21 Nov 2026:
// the screen is a simulation of what the learner builds on the mat). Their components are
// still in ui/; to bring them back, put <TutorPanel /> and <ConceptMap /> in a second column.

import { Bench } from './bench/Bench'
import { HapticsProvider } from './haptics/HapticsContext'
import { Instrument } from './Instrument'
import { CameraCorner } from './ui/CameraCorner'
import { StatusBar } from './ui/StatusBar'

export default function App() {
  return (
    <HapticsProvider>
      <Instrument />
      {/* Wide (the projector): everything fits the screen with no scrolling. Narrow: the
          pieces stack and the page scrolls. */}
      <div className="flex min-h-full flex-col gap-4 p-4 lg:h-full lg:p-6">
        <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-rows-[minmax(0,1fr)]">
          <Bench>
            <CameraCorner />
          </Bench>
        </main>
        <StatusBar />
      </div>
    </HapticsProvider>
  )
}
