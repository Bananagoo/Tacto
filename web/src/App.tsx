// Tinker keeps the bench open-ended. Lab adds prompts and spoken reflections above it.
// The parked tutor and concept map remain out of the layout.

import { Bench } from './bench/Bench'
import { HapticsProvider } from './haptics/HapticsContext'
import { Instrument } from './Instrument'
import { CameraCorner } from './ui/CameraCorner'
import { LessonStrip } from './ui/LessonStrip'
import { StatusBar } from './ui/StatusBar'

export default function App({ onHome }: { onHome: () => void }) {
  return (
    <HapticsProvider>
      <Instrument />
      {/* Wide (the projector): everything fits the screen with no scrolling. Narrow: the
          pieces stack and the page scrolls. */}
      <div className="flex min-h-full flex-col gap-4 p-4 lg:h-full lg:p-6">
        <LessonStrip />
        <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-rows-[minmax(0,1fr)]">
          <Bench onHome={onHome}>
            <CameraCorner />
          </Bench>
        </main>
        <StatusBar />
      </div>
    </HapticsProvider>
  )
}
