// Layout only: the bench on the left, the tutor, the concept map and the camera corner on the
// right, the status bar along the bottom. Each piece reads what it needs from the store itself.

import { Bench } from './bench/Bench'
import { HapticsProvider } from './haptics/HapticsContext'
import { Instrument } from './Instrument'
import { CameraCorner } from './ui/CameraCorner'
import { ConceptMap } from './ui/ConceptMap'
import { StatusBar } from './ui/StatusBar'
import { TutorPanel } from './ui/TutorPanel'

export default function App() {
  return (
    <HapticsProvider>
      <Instrument />
      {/* Wide (the projector): everything fits the screen with no scrolling. Narrow: the
          pieces stack and the page scrolls. */}
      <div className="flex min-h-full flex-col gap-4 p-4 lg:h-full lg:p-6">
        <main className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[3fr_2fr] lg:grid-rows-[minmax(0,1fr)]">
          <Bench />
          <div className="flex min-h-0 flex-col gap-4">
            <TutorPanel />
            <ConceptMap />
            <CameraCorner />
          </div>
        </main>
        <StatusBar />
      </div>
    </HapticsProvider>
  )
}
