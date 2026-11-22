// Launch page first, then the lab or the gallery. The lab lives at #lab and the gallery at
// #gallery, so a reload stays where it is and the browser's Back button returns to the launch
// page. The lab (and its WebSocket) only mounts once it is opened.

import { useEffect, useState } from 'react'
import App from './App'
import { Gallery } from './ui/Gallery'
import { Launch } from './ui/Launch'

const LAB_HASH = '#lab'
const GALLERY_HASH = '#gallery'

export default function Root() {
  const [hash, setHash] = useState(location.hash)
  useEffect(() => {
    const onChange = () => setHash(location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  if (hash === LAB_HASH) return <App onHome={() => (location.hash = '')} />
  if (hash === GALLERY_HASH) return <Gallery onBack={() => (location.hash = '')} />
  return (
    <Launch
      onOpen={() => (location.hash = LAB_HASH)}
      onOpenGallery={() => (location.hash = GALLERY_HASH)}
    />
  )
}
