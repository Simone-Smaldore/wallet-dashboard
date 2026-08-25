import type { ButtonHTMLAttributes } from 'react'
import type { LucideIcon } from 'lucide-react'

/** A control that is only an icon.
 *
 * ⚠️ `label` is required and lands in **both** `aria-label` and `title`: the
 * first is what a screen reader announces, the second is the tooltip a mouse
 * gets. An icon on its own is a guess — and on desktop, where there is a
 * pointer and no space constraint, there is no reason to make anyone guess.
 *
 * Having the two come from one prop is the point: they cannot drift, and a new
 * icon button cannot be added without a name.
 */

type Size = 'sm' | 'md'

const SIZES: Record<Size, string> = {
  // Tighter on a phone, where a row has to hold three of them next to a name.
  sm: 'size-8 sm:size-9',
  md: 'size-10',
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  Icon: LucideIcon
  size?: Size
  iconSize?: number
}

export function IconButton({
  label,
  Icon,
  size = 'sm',
  iconSize = 18,
  className = '',
  ...rest
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={[
        'grid shrink-0 place-items-center rounded-pill text-ink-3',
        'transition-colors duration-200 hover:bg-surface-hover hover:text-ink-1',
        'disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-ink-3',
        SIZES[size],
        className,
      ].join(' ')}
      {...rest}
    >
      <Icon size={iconSize} strokeWidth={2} aria-hidden />
    </button>
  )
}
