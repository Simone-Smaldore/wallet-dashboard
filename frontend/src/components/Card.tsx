import type { ReactNode } from 'react'

/** The only container in the app: card surface, hairline border, deep shadow.
 *  Two background colours per screen — the page and this. */
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-card border border-border-soft bg-surface-card p-5 shadow-card ${className}`}
    >
      {children}
    </section>
  )
}
