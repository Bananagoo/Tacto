// Tooling for the people building Tacto, at /devtools/. Not part of the product:
// nothing under src/ may import from this folder (server/tests/test_boundaries.py).
// Run it with `make bench`, which serves the product on a virtual mat and the camera routes.

import { useEffect, useState } from 'react'
import CameraPanel from './camera/CameraPanel'
import HapticTestPage from './haptics/HapticTestPage'
import MatPanel from './mat/MatPanel'

const TOOLS = [
  { hash: '#mat', label: 'Virtual mat', render: () => <MatPanel /> },
  {
    hash: '#camera',
    label: 'Camera',
    render: () => (
      <main className="mx-auto max-w-6xl p-8">
        <CameraPanel />
      </main>
    ),
  },
  { hash: '#haptics', label: 'Haptics', render: () => <HapticTestPage /> },
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
      <nav className="flex items-center gap-2 border-b border-white/10 px-8 py-3">
        <span className="mr-4 font-semibold">Tacto dev tools</span>
        {TOOLS.map((candidate) => (
          <a
            key={candidate.hash}
            href={candidate.hash}
            className={`rounded px-3 py-1 ${candidate === tool ? 'bg-white/15' : 'opacity-70 hover:opacity-100'}`}
          >
            {candidate.label}
          </a>
        ))}
      </nav>
      {/* key: switching tools must unmount the old one so it releases the camera or the mouse. */}
      <div key={tool.hash}>{tool.render()}</div>
    </div>
  )
}
