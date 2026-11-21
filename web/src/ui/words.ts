/** An id from the lesson as words for the screen: `closed_loop` becomes "Closed loop". */
export function toWords(id: string): string {
  const words = id.replace(/[_-]+/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}
