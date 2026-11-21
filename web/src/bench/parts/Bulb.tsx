import ledBrightUrl from '../../assets/LedBright.png'
import ledDimUrl from '../../assets/LedDim.png'
import ledOffUrl from '../../assets/LedOff.png'
import { Leads } from './Leads'

// The LED is drawn in a box this big and each picture is fitted into it, so the three never
// jump about when one swaps for another.
const BOX_WIDTH = 60
const BOX_HEIGHT = 150
// Room the LED takes on the wire, so the two leads stop short of it.
const BODY_WIDTH = 40
// Where the three pictures change, on the server's 0 to 1 brightness.
// TODO(front end owner): tune by eye once real circuits run. Series bulbs sit at 0.25, a
// single bulb or a parallel branch at 1.
const OFF_BELOW = 0.02
const BRIGHT_FROM = 0.6

interface BulbProps {
  length: number
  /** Which way the part's own axis turns the drawing, so the LED can be stood back upright. */
  angleDeg: number
  /** 0 (off) to 1 (full), from the server. */
  brightness: number
}

function pictureFor(brightness: number): { url: string; words: string } {
  const level = Number.isFinite(brightness) ? brightness : 0
  if (level < OFF_BELOW) return { url: ledOffUrl, words: 'LED, off' }
  if (level < BRIGHT_FROM) return { url: ledDimUrl, words: 'LED, dim' }
  return { url: ledBrightUrl, words: 'LED, bright' }
}

/**
 * A lamp, drawn as an LED in one of three pictures: off, dim or bright. Brightness shows in
 * the picture's glow, and the three also differ in colour depth, so they read apart in
 * greyscale. The LED always stands upright, whichever way its two dots run.
 */
export function Bulb({ length, angleDeg, brightness }: BulbProps) {
  const { url, words } = pictureFor(brightness)
  return (
    <>
      <Leads length={length} bodyWidth={BODY_WIDTH} />
      <g transform={`translate(${length / 2} 0) rotate(${-angleDeg})`}>
        <image
          href={url}
          x={-BOX_WIDTH / 2}
          y={-BOX_HEIGHT / 2}
          width={BOX_WIDTH}
          height={BOX_HEIGHT}
          preserveAspectRatio="xMidYMid meet"
          aria-label={words}
        />
      </g>
    </>
  )
}
