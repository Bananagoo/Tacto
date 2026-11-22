// Calls to the tooling server's /dev routes (server/tacto_bench/camera_routes.py).
// The camera bench is a hardware tool, not the product, so it talks to the server
// directly instead of going through the useTacto store. Needs `make bench`.

export interface CameraInfo {
  index: number
  name: string
}

export interface Fingertip {
  handedness: string
  x: number
  y: number
}

export interface CameraStatus {
  open: boolean
  fps?: number
  error?: string | null
  width?: number
  height?: number
  brightness?: number
  sharpness?: number
  mat_found?: boolean
  mat_held?: boolean
  /** A corner was read in this frame. False while the picture is too soft to read any. */
  mat_confirmed?: boolean
  corners_seen?: number[]
  /** Autofocus sweeps started because no corner could be read. */
  focus_kicks?: number
  /** Milliseconds this frame took to flatten and to read. */
  flatten_ms?: number
  read_ms?: number
  /** Segment id -> what the reader saw there, for every segment that is not empty. */
  pieces?: Record<string, string>
  /** How many of the seven colour squares have been read off the mat. */
  squares_seen?: number
  marker_ids?: number[]
  missing_corners?: number[]
  corners_visible?: boolean
  fingertips?: Fingertip[]
  hand_error?: string
}

/** How the LogiInsight camera is exposing. `available` is false until `make camera-tool` has run. */
export interface Exposure {
  available: boolean
  camera_found: boolean
  manual: boolean
  gain: number
}

export async function getExposure(): Promise<Exposure> {
  const response = await fetch('/api/dev/camera/exposure')
  if (!response.ok) throw new Error(`server answered ${response.status}`)
  return (await response.json()) as Exposure
}

export async function setExposure(manual: boolean, gain: number): Promise<Exposure> {
  const response = await fetch('/api/dev/camera/exposure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ manual, gain }),
  })
  if (!response.ok) throw new Error(`server answered ${response.status}`)
  return (await response.json()) as Exposure
}

export type Overlay = 'aruco' | 'hand'

export async function listCameras(): Promise<CameraInfo[]> {
  const response = await fetch('/api/dev/cameras')
  if (!response.ok) throw new Error(`server answered ${response.status}`)
  const body = (await response.json()) as { cameras: CameraInfo[] }
  return body.cameras
}

export async function cameraStatus(index: number): Promise<CameraStatus> {
  const response = await fetch(`/api/dev/camera/status?index=${index}`)
  if (!response.ok) throw new Error(`server answered ${response.status}`)
  return (await response.json()) as CameraStatus
}

/**
 * `nonce` forces a fresh connection when the same camera is restarted. `flat` asks for
 * the mat squared up, as the reader sees it, instead of the camera's picture.
 */
export function streamUrl(
  index: number,
  overlays: Overlay[],
  nonce: number,
  flat: boolean,
  read: boolean,
): string {
  return `/api/dev/camera/stream?index=${index}&overlay=${overlays.join(',')}&flat=${flat ? 1 : 0}&read=${read ? 1 : 0}&n=${nonce}`
}
