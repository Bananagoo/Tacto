import ledBrightUrl from '../../assets/LedBright.png'
import ledDimUrl from '../../assets/LedDim.png'
import ledOffUrl from '../../assets/LedOff.png'
import { Leads } from './Leads'

// The LED is drawn this wide (a dot pitch is 100), with its legs bent out to the two sides. Its
// dome then stands about 120 above the wire, which fits the margin round the mat's top row (grid.ts). Where the
// dots are closer than this it shrinks to fit, so the leg tips always reach them; where they are
// further apart a plain lead joins each dot to a leg tip.
const MAX_WIDTH = 160
// The box is a little taller than any picture, and each picture sits at its bottom, so the three
// line up when one swaps for another.
const BOX_HEIGHT_PER_WIDTH = 0.8
// The legs' middle sits this far (as a share of the width) above the pictures' bottom edge, so
// they lie on the line between the dots.
const LEG_DROP_PER_WIDTH = 0.036
// Where the three pictures change, on the server's 0 to 1 brightness (the bulb's power, so it
// goes with the square of the current: 1 is 0.6 A).
// TODO(front end owner): tune by eye. At 6 V a single bulb or a parallel branch is 1 (bright)
// and two bulbs in series 0.25 (dim). A bulb in series with the resistor reaches only 0.56 even
// at 9 V; it was stuck on dim at 0.6 (22 Nov 2026), so bright now starts at 0.5, about 0.42 A.
const OFF_BELOW = 0.02
const BRIGHT_FROM = 0.5

interface BulbProps {
  length: number
  /** The part's direction, so an LED pointing left is not drawn upside down. */
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
 * the glow, and the three also differ in colour depth, so they read apart in greyscale. Its
 * legs run along the part's two dots (a plain lead fills any gap), and its dome points up unless the part is turned past
 * a quarter turn, where it is flipped so it is never upside down.
 */
export function Bulb({ length, angleDeg, brightness }: BulbProps) {
  const { url, words } = pictureFor(brightness)
  const flip = Math.abs(angleDeg) > 90
  const width = Math.min(MAX_WIDTH, length)
  const height = width * BOX_HEIGHT_PER_WIDTH
  return (
    <>
      <Leads length={length} bodyWidth={width} />
      <g transform={`translate(${length / 2} 0) rotate(${flip ? 180 : 0})`}>
        <image
          href={url}
          x={-width / 2}
          y={width * LEG_DROP_PER_WIDTH - height}
          width={width}
          height={height}
          preserveAspectRatio="xMidYMax meet"
          aria-label={words}
        />
      </g>
    </>
  )
}
