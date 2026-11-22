// Tooling for the people building Tacto, at /devtools/. Not part of the product:
// nothing under src/ may import from this folder (server/tests/test_boundaries.py).
// The camera and haptics pages need `make bench`; the live state page needs `make dev` or
// `make mock`.

import { useEffect, useState } from 'react'
import CameraPanel from './camera/CameraPanel'
import HapticTestPage from './haptics/HapticTestPage'
import SetupCheck from './setup/SetupCheck'
import logoUrl from '../src/assets/Logo.png'
import StatePanel from './state/StatePanel'

const TOOLS = [
  // Before a demo: finds the camera brightness for the room and checks it will all work.
  // Needs make dev.
  { hash: '#setup', label: 'Setup check', needs: 'make dev', render: () => <SetupCheck /> },
  {
    hash: '#camera',
    label: 'Camera bench',
    needs: 'make bench',
    render: () => (
      <main className="mx-auto max-w-6xl p-8">
        <CameraPanel />
      </main>
    ),
  },
  { hash: '#haptics', label: 'Haptics', needs: '', render: () => <HapticTestPage /> },
  // The live state message drawn plainly. Works with make dev and make mock.
  {
    hash: '#state',
    label: 'Live state',
    needs: 'make dev or make mock',
    render: () => <StatePanel />,
  },
]

export default function DevTools() {
  const [hash, setHash] = useState(location.hash)
  useEffect(() => {
    const onChange = () => setHash(location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  const tool = TOOLS.find((candidate) => candidate.hash === hash) ?? TOOLS[0]

  return (
    <div className="flex min-h-full flex-col">
      {/* The same bar as the lab's: Tacto's logo and handwriting, tools as a row of pills. */}
      <nav className="flex flex-wrap items-center gap-3 px-6 py-4 font-['Patrick_Hand'] lg:px-8">
        <a
          href="/"
          title="Back to Tacto"
          className="flex items-center gap-3 rounded-2xl bg-white/5 px-4 py-2 text-xl text-stone-200 hover:bg-white/10 hover:text-white"
        >
          <img src={logoUrl} alt="" className="h-8 w-auto" />
          Tacto
        </a>
        <span className="text-xl text-stone-400">dev tools</span>
        <div role="tablist" className="ml-2 flex flex-wrap gap-1 rounded-2xl bg-white/5 p-1">
          {TOOLS.map((candidate) => (
            <a
              key={candidate.hash}
              href={candidate.hash}
              role="tab"
              aria-selected={candidate === tool}
              className={`rounded-xl px-5 py-1.5 text-xl ${
                candidate === tool ? 'bg-white/15 text-white' : 'text-stone-400 hover:text-white'
              }`}
            >
              {candidate.label}
            </a>
          ))}
        </div>
        {tool.needs && <span className="ml-auto text-lg text-stone-400">needs {tool.needs}</span>}
      </nav>
      {/* key: switching tools must unmount the old one so it releases the camera or the mouse. */}
      <div key={tool.hash} className="flex-1">
        {tool.render()}
      </div>
    </div>
  )
}
