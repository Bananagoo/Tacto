import { useEffect, useRef, useState } from 'react'
import {
  cameraStatus,
  listCameras,
  streamUrl,
  type CameraInfo,
  type CameraStatus,
  type Overlay,
} from './api'

const STATUS_EVERY_MS = 500
const PREFERRED_CAMERA = 'LVNext'

export default function CameraPanel() {
  const [cameras, setCameras] = useState<CameraInfo[]>([])
  const [listError, setListError] = useState('')
  const [index, setIndex] = useState(0)
  const [running, setRunning] = useState(false)
  const [nonce, setNonce] = useState(0)
  const [aruco, setAruco] = useState(true)
  const [hand, setHand] = useState(false)
  const [status, setStatus] = useState<CameraStatus | null>(null)
  const [streamError, setStreamError] = useState('')
  const image = useRef<HTMLImageElement>(null)

  const loadCameras = () => {
    listCameras()
      .then((found) => {
        setListError('')
        setCameras(found)
        const preferred = found.find((camera) => camera.name.includes(PREFERRED_CAMERA))
        if (preferred) setIndex(preferred.index)
      })
      .catch((error: unknown) =>
        setListError(`Could not reach the server (${String(error)}). Is make dev running?`),
      )
  }
  useEffect(loadCameras, [])

  const overlays: Overlay[] = [
    ...(aruco ? (['aruco'] as const) : []),
    ...(hand ? (['hand'] as const) : []),
  ]
  const source = running ? streamUrl(index, overlays, nonce) : ''

  // The server keeps the camera open for as long as this <img> holds the stream,
  // so drop the connection explicitly when stopping or leaving the page.
  useEffect(() => {
    const element = image.current
    return () => {
      if (element) element.src = ''
    }
  }, [source])

  useEffect(() => {
    if (!running) return
    const timer = setInterval(() => {
      cameraStatus(index)
        .then(setStatus)
        .catch(() => setStatus(null))
    }, STATUS_EVERY_MS)
    return () => clearInterval(timer)
  }, [running, index])

  const start = () => {
    setStreamError('')
    setStatus(null)
    setNonce((value) => value + 1)
    setRunning(true)
  }
  const stop = () => {
    setRunning(false)
    setStatus(null)
  }

  const shown = running ? status : null

  return (
    <section className="flex flex-col gap-4 rounded-xl bg-white/5 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-2 text-xl font-semibold">Camera</h2>
        <select
          className="rounded bg-white/10 px-2 py-1"
          value={index}
          disabled={running}
          onChange={(event) => setIndex(Number(event.target.value))}
        >
          {cameras.length === 0 && <option value={0}>camera 0</option>}
          {cameras.map((camera) => (
            <option key={camera.index} value={camera.index}>
              {camera.index}: {camera.name}
            </option>
          ))}
        </select>
        <button
          className="rounded bg-white/10 px-3 py-1 hover:bg-white/20 disabled:opacity-40"
          disabled={running}
          onClick={loadCameras}
        >
          Refresh list
        </button>
        <button
          className={`rounded px-4 py-1 font-medium ${running ? 'bg-rose-500/80 hover:bg-rose-500' : 'bg-emerald-500/80 hover:bg-emerald-500'}`}
          onClick={running ? stop : start}
        >
          {running ? 'Stop camera' : 'Start camera'}
        </button>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={aruco} onChange={(e) => setAruco(e.target.checked)} />
          Markers
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={hand} onChange={(e) => setHand(e.target.checked)} />
          Hand points
        </label>
      </div>

      {listError && <p className="text-rose-400">{listError}</p>}
      {streamError && <p className="text-rose-400">{streamError}</p>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-black">
          {running ? (
            <img
              // A new element per stream: changing an overlay then starts a fresh
              // connection, and closing the old one cannot blank the new one.
              key={source}
              ref={image}
              src={source}
              alt="Live camera"
              className="h-full w-full object-contain"
              onError={() => {
                setStreamError(
                  'The camera stream stopped. Check it is plugged in and that the terminal running the server has Camera permission.',
                )
                setRunning(false)
              }}
            />
          ) : (
            <p className="opacity-60">Camera is off. It only runs while this view is on.</p>
          )}
        </div>

        <dl className="grid h-fit grid-cols-[auto_1fr] gap-x-4 gap-y-1">
          <dt className="opacity-60">Frame rate</dt>
          <dd>{shown?.fps != null ? `${shown.fps.toFixed(1)} fps` : '–'}</dd>
          <dt className="opacity-60">Size</dt>
          <dd>{shown?.width ? `${shown.width}×${shown.height}` : '–'}</dd>
          <dt className="opacity-60">Brightness</dt>
          <dd>{shown?.brightness != null ? `${shown.brightness.toFixed(0)} / 255` : '–'}</dd>
          {aruco && (
            <>
              <dt className="opacity-60">Markers</dt>
              <dd>{shown?.marker_ids ? shown.marker_ids.join(', ') || 'none' : '–'}</dd>
              <dt className="opacity-60">Corners</dt>
              <dd
                className={
                  shown?.corners_visible == null
                    ? ''
                    : shown.corners_visible
                      ? 'text-emerald-400'
                      : 'text-amber-300'
                }
              >
                {shown?.corners_visible == null
                  ? '–'
                  : shown.corners_visible
                    ? 'all four visible'
                    : `missing ${shown.missing_corners?.join(', ')}`}
              </dd>
            </>
          )}
          {hand && (
            <>
              <dt className="opacity-60">Index tip</dt>
              <dd className={shown?.hand_error ? 'text-rose-400' : ''}>
                {shown?.hand_error ??
                  (shown?.fingertips
                    ? shown.fingertips
                        .map((tip) => `${tip.handedness} (${tip.x}, ${tip.y})`)
                        .join('; ') || 'no hand'
                    : '–')}
              </dd>
            </>
          )}
          {shown?.error && (
            <>
              <dt className="opacity-60">Error</dt>
              <dd className="text-rose-400">{shown.error}</dd>
            </>
          )}
        </dl>
      </div>
    </section>
  )
}
