// Saves a picture of the circuit on the mat to the learner's own device. Nothing is sent
// anywhere: the picture is made in the page and handed to the browser as a download.

// The mat's styles come from the page's CSS classes, which a loose copy of the drawing would
// lose, so each element's look is written onto it before it is turned into a picture.
const LOOK = [
  'fill',
  'stroke',
  'stroke-width',
  'stroke-linecap',
  'stroke-dasharray',
  'stroke-dashoffset',
  'opacity',
  'font-family',
  'font-size',
  'font-weight',
]

const SCALE = 2
// The mat's green, drawn behind the circuit because the page's own background is not part of the svg.
const MAT_GREEN = '#006045'

/** Parts of the drawing that are not the circuit (the multimeter) carry this and are left out. */
export const SKIP_IN_SCREENSHOT = 'data-skip-in-screenshot'

function drawnCopy(svg: SVGSVGElement): SVGSVGElement {
  const copy = svg.cloneNode(true) as SVGSVGElement
  const before: Element[] = [svg, ...svg.querySelectorAll('*')]
  const after = [copy, ...copy.querySelectorAll<SVGElement>('*')]
  before.forEach((original, index) => {
    const look = getComputedStyle(original)
    for (const property of LOOK)
      after[index].style.setProperty(property, look.getPropertyValue(property))
  })
  copy.querySelectorAll(`[${SKIP_IN_SCREENSHOT}]`).forEach((element) => element.remove())

  const { width, height } = svg.viewBox.baseVal
  copy.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  copy.setAttribute('width', String(width * SCALE))
  copy.setAttribute('height', String(height * SCALE))
  copy.style.opacity = '1'
  const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  background.setAttribute('width', String(width))
  background.setAttribute('height', String(height))
  background.setAttribute('fill', MAT_GREEN)
  copy.insertBefore(background, copy.firstChild)
  return copy
}

// A picture made from an svg cannot load other files, so each drawing in it (the battery) is
// written into it as data.
async function inlineImages(copy: SVGSVGElement): Promise<void> {
  const images = Array.from(copy.querySelectorAll('image'))
  await Promise.all(
    images.map(async (image) => {
      const href = image.getAttribute('href')
      if (!href || href.startsWith('data:')) return
      const blob = await (await fetch(href)).blob()
      const data = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result))
        reader.onerror = () => reject(reader.error)
        reader.readAsDataURL(blob)
      })
      image.setAttribute('href', data)
    }),
  )
}

/** Turn the mat's svg into a PNG and download it. Rejects if the browser cannot draw it. */
export async function saveScreenshot(svg: SVGSVGElement): Promise<void> {
  const copy = drawnCopy(svg)
  await inlineImages(copy)
  const url = URL.createObjectURL(
    new Blob([new XMLSerializer().serializeToString(copy)], { type: 'image/svg+xml' }),
  )
  return new Promise((resolve, reject) => {
    const picture = new Image()
    picture.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = picture.width
      canvas.height = picture.height
      canvas.getContext('2d')?.drawImage(picture, 0, 0)
      URL.revokeObjectURL(url)
      canvas.toBlob((png) => {
        if (!png) return reject(new Error('could not make the picture'))
        const link = document.createElement('a')
        link.href = URL.createObjectURL(png)
        link.download = `tacto-circuit-${new Date().toISOString().replace(/[:.]/g, '-')}.png`
        link.click()
        URL.revokeObjectURL(link.href)
        resolve()
      }, 'image/png')
    }
    picture.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('could not draw the circuit'))
    }
    picture.src = url
  })
}
