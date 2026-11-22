import ledBrightUrl from '../../assets/LedBright.png'
import ledDimUrl from '../../assets/LedDim.png'
import ledOffUrl from '../../assets/LedOff.png'

// Each picture is about 3 wide to 2.2 high, with its legs bent out to the two sides. It is drawn
// as wide as the part is long, so the leg tips reach the two dots. The box is a little taller than
// any picture, and each picture sits at its bottom, so the three line up when one swaps for another.
const BOX_HEIGHT_PER_LENGTH = 0.8
// The legs' middle sits this far (as a share of the length) above the pictures' bottom edge, so
// they lie on the line between the dots.
const LEG_DROP_PER_LENGTH = 0.036
// Where the three pictures change, on the server's 0 to 1 brightness.
// TODO(front end owner): tune by eye once real circuits run. Series bulbs sit at 0.25, a
// single bulb or a parallel branch at 1.
const OFF_BELOW = 0.02
const BRIGHT_FROM = 0.6

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
 * legs run along the part's two dots, and its dome points up unless the part is turned past
 * a quarter turn, where it is flipped so it is never upside down.
 */
export function Bulb({ length, angleDeg, brightness }: BulbProps) {
  const { url, words } = pictureFor(brightness)
  const flip = Math.abs(angleDeg) > 90
  const height = length * BOX_HEIGHT_PER_LENGTH
  return (
    <g transform={`translate(${length / 2} 0) rotate(${flip ? 180 : 0})`}>
      <image
        href={url}
        x={-length / 2}
        y={length * LEG_DROP_PER_LENGTH - height}
        width={length}
        height={height}
        preserveAspectRatio="xMidYMax meet"
        aria-label={words}
      />
    </g>
  )
}
