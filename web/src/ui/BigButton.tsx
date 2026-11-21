interface BigButtonProps {
  label: string
  disabled: boolean
  onPress: () => void
}

/** The one button style of the lesson: big enough to read and to hit from a standing start. */
export function BigButton({ label, disabled, onPress }: BigButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onPress}
      className="cursor-pointer rounded-2xl bg-stone-100 px-8 py-5 text-3xl font-semibold text-stone-900 hover:bg-white focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-sky-300 disabled:cursor-default disabled:opacity-40"
    >
      {label}
    </button>
  )
}
