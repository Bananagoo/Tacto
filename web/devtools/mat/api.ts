// Calls to the tooling server's /dev/mat routes (server/tacto_bench/mat_routes.py).
// The virtual mat stands in for the paper and the camera. Needs `make bench`.

export type Dot = [col: number, row: number]
export type SlotContent = 'empty' | 'wire' | 'bulb' | 'resistor' | 'switch'

interface Segment {
  a: Dot
  b: Dot
}

export interface MatLayout {
  id: string
  cols: number
  rows: number
  parts: (Segment & { id: string; kind: string })[]
  wires: Segment[]
  drawables: (Segment & { id: string })[]
  slots: (Segment & { id: string; accepts: SlotContent[] })[]
}

export interface MatView {
  layout: MatLayout
  drawn: string[]
  slots: Record<string, SlotContent>
  fingertip: { x: number; y: number } | null
}

async function call(path: string, body?: unknown): Promise<MatView> {
  const response = await fetch(`/api/dev/mat${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`server answered ${response.status}`)
  return (await response.json()) as MatView
}

export const getMat = () => call('')
export const setDrawn = (id: string, drawn: boolean) => call('/draw', { id, drawn })
export const setSlot = (id: string, content: SlotContent) => call('/slot', { id, content })
export const setFingertip = (fingertip: MatView['fingertip']) => call('/finger', { fingertip })
export const resetMat = () => call('/reset', {})
