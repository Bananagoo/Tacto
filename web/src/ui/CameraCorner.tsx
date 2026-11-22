import { useState } from 'react'
import { useTacto } from '../useTacto'

/**
 * A small live picture from the camera above the desk, so the room sees what the learner's
 * hands are doing while the bench shows what Tacto made of it. It sits over the bench's
 * bottom-right corner, where the mat is empty, so it never takes room from the tutor. It is a plain picture stream
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
    <figure
      key={String(connected)}
      className="absolute right-4 bottom-4 w-56 overflow-hidden rounded-2xl bg-stone-900 ring-1 ring-white/20"
    >
      <img
        src="/api/camera/preview"
        alt="Live view of the desk"
        onError={() => setFailed(true)}
        // Mirrored, like a selfie camera, so the learner's right hand is on the right of the
        // picture. Only this picture: the server reads the frame as the camera sent it.
        className="aspect-video w-full -scale-x-100 object-cover"
      />
    </figure>
  )
}
