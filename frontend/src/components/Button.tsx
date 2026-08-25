import type { ButtonHTMLAttributes, ReactNode } from 'react'

/** Buttons are pills at 999px — DESIGN.md has no sharp corners anywhere.
 *
 * ⚠️ One `primary` per screen. The glow belongs to the primary action and the
 * FAB and nowhere else: spread around, it stops meaning "this is the thing to
 * press" and becomes decoration.
 */

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-ink-on-accent shadow-glow-accent hover:bg-accent-hover active:bg-accent-press',
  secondary: 'border border-border-strong text-ink-1 hover:bg-surface-hover',
  ghost: 'text-ink-2 hover:bg-surface-hover hover:text-ink-1',
  danger: 'border border-border-strong text-danger hover:bg-danger-dim',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
}

export function Button({ variant = 'primary', className = '', children, ...rest }: ButtonProps) {
  return (
    <button
      className={[
        'inline-flex min-h-11 items-center justify-center gap-2 rounded-pill px-4 py-3',
        'text-body font-medium transition-colors duration-200',
        'disabled:cursor-not-allowed disabled:opacity-45',
        VARIANTS[variant],
        className,
      ].join(' ')}
      {...rest}
    >
      {children}
    </button>
  )
}
