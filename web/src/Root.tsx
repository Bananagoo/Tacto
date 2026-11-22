// Launch page first, then the lab. The lab lives at #lab so a reload stays in it and the
// browser's Back button returns to the launch page. The lab (and its WebSocket) only
// mounts once it is opened.

import { useEffect, useState } from 'react'
import App from './App'
import { Launch } from './ui/Launch'

const LAB_HASH = '#lab'

export default function Root() {
  const [hash, setHash] = useState(location.hash)
  useEffect(() => {
    const onChange = () => setHash(location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  if (hash === LAB_HASH) return <App />
  return <Launch onOpen={() => (location.hash = LAB_HASH)} />
}
