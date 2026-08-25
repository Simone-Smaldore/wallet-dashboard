import type { ReactNode } from 'react'

/** The card every chart sits in: a title, an optional aside, and the drawing.
 *
 * ⚠️ **It owns the empty case.** When there is nothing to draw it says so in a
 * sentence and never renders the chart. A grid with its axes at zero reads as
 * "you spent nothing", which is a different claim from "you recorded nothing" —
 * and the first is one you would believe. Handling it here means seven charts
 * cannot each get it slightly wrong.
 */
export function ChartFrame({
  title,
  aside,
  empty,
  emptyText = 'Nessun movimento in questo periodo.',
  children,
}: {
  title: string
  /** Small text on the right of the title: a total, a comparison. */
  aside?: ReactNode
  empty: boolean
  emptyText?: string
  children: ReactNode
}) {
  return (
    <section className="rounded-card border border-border-soft bg-surface-card p-4 shadow-card sm:p-5">
      <header className="flex items-baseline justify-between gap-3">
        <h2 className="font-display text-heading text-ink-1">{title}</h2>
        {aside ? <div className="shrink-0 text-caption text-ink-2">{aside}</div> : null}
      </header>

      {empty ? (
        <p className="py-8 text-center text-body text-ink-2">{emptyText}</p>
      ) : (
        <div className="mt-4">{children}</div>
      )}
    </section>
  )
}
