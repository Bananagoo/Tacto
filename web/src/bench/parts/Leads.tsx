interface LeadsProps {
  /** Distance between the part's two dots. */
  length: number
  /** Width of the symbol sitting in the middle. */
  bodyWidth: number
}

/**
 * The two straight legs that join a symbol to its dots. Drawn along the x axis from 0 to
 * `length`. When the dots are closer than the symbol is wide there is nothing to draw.
 */
export function Leads({ length, bodyWidth }: LeadsProps) {
  const lead = (length - bodyWidth) / 2
  if (lead <= 0) return null
  return (
    <>
      <line x1={0} y1={0} x2={lead} y2={0} />
      <line x1={length - lead} y1={0} x2={length} y2={0} />
    </>
  )
}
