/** What the meter's dial is set to: amps, volts or ohms. */
export type MeterMode = 'A' | 'V' | 'Ω'

/** The dial's settings in the order it turns through them. */
export const METER_MODES: readonly MeterMode[] = ['A', 'V', 'Ω']

/** The setting `steps` clicks of the dial away, wrapping round. */
export function turnDial(mode: MeterMode, steps: number): MeterMode {
  const count = METER_MODES.length
  const at = METER_MODES.indexOf(mode)
  return METER_MODES[(((at + steps) % count) + count) % count]
}
