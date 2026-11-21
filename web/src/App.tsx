// The product shell. The lesson view (bench, tutor panel, concept map) is added in the
// next build wave; until then this shows the connection and the tutor's current line.

import { Bench } from './bench/Bench'
import { useTacto, useTactoConnection } from './useTacto'

// Server-chosen haptic effects are wired up together with the product's haptics.
const ignoreHaptic = () => {}

export default function App() {
  useTactoConnection(ignoreHaptic)
  const { connected, state } = useTacto()

  return (
    <main className="mx-auto flex h-full max-w-5xl flex-col justify-center gap-4 p-8">
      <h1 className="text-4xl font-semibold">Tacto</h1>
      <p className="text-2xl opacity-80">
        {connected
          ? state?.tutor.prompt || 'Waiting for the lesson to start.'
          : 'Connecting to the Tacto server…'}
      </p>
      <Bench />
    </main>
  )
}
