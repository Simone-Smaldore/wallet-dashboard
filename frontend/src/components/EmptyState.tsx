import type { ReactNode } from 'react'

/** What a screen says when it has nothing to show.
 *
 * ⚠️ A period with no data is said in words, never drawn as an empty chart: an
 * axis at zero reads as "you spent nothing", which is a different claim from
 * "nothing was recorded".
 */
export function EmptyState({
  title,
  children,
  action,
}: {
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <p className="font-display text-heading text-ink-1">{title}</p>
      {children ? <p className="max-w-[42ch] text-body text-ink-2">{children}</p> : null}
      {action}
    </div>
  )
}
