// Hardware test bench at /#test. For checking the camera and the mouse by hand;
// not part of what the learner sees.

import CameraPanel from './CameraPanel'

export default function TestBench() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 p-8">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Tacto hardware test bench</h1>
        <a className="underline opacity-70 hover:opacity-100" href="#">
          Back to the dev harness
        </a>
      </header>
      <CameraPanel />
    </main>
  )
}
