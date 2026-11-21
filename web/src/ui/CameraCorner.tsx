import { useState } from 'react'
import { useTacto } from '../useTacto'

/**
 * A small live picture from the camera above the desk, so the room sees what the learner's
 * hands are doing while the bench shows what Tacto made of it. It is a plain picture stream
 * from the server (never stored) and renders nothing without a camera: replay, the virtual
 * mat, or a camera that failed to open.
 */
export function CameraCorner() {
  const onCamera = useTacto((store) => store.state?.source === 'camera')
  const connected = useTacto((store) => store.connected)
  const [failed, setFailed] = useState(false)
  if (!onCamera || failed) return null
  return (
    // key: coming back from a dropped connection starts a fresh stream.
    <figure key={String(connected)} className="shrink-0 overflow-hidden rounded-3xl bg-white/5">
      <img
        src="/api/camera/preview"
        alt="Live view of the desk"
        onError={() => setFailed(true)}
        className="aspect-video w-full object-cover"
      />
      <figcaption className="px-4 py-2 text-lg text-stone-300">What the camera sees</figcaption>
    </figure>
  )
}
