// Tinker keeps the bench open-ended. Lab adds prompts and spoken reflections above it.
// The parked tutor and concept map remain out of the layout.

import { Bench } from './bench/Bench'
import { HapticsProvider } from './haptics/HapticsContext'
import { Instrument } from './Instrument'
import { CameraCorner } from './ui/CameraCorner'
import { LessonPanel, ModeBar } from './ui/LessonStrip'

export default function App() {
  return (
    <HapticsProvider>
      <Instrument />
      {/* Wide (the projector): everything fits the screen with no scrolling. Narrow: the
          pieces stack and the page scrolls. */}
      <div className="flex min-h-full flex-col gap-4 p-4 lg:h-full lg:p-6">
        <ModeBar />
        {/* Wide: the lesson stands beside the mat, which keeps its full height. Narrow:
            the lesson comes first and the mat follows below it. */}
        <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row-reverse">
          <LessonPanel />
          <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-rows-[minmax(0,1fr)]">
            <Bench>
              <CameraCorner />
            </Bench>
          </main>
        </div>
      </div>
    </HapticsProvider>
  )
}
