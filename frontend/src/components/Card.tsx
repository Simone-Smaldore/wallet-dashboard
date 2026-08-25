import type { ReactNode } from 'react'

/** The only container in the app: card surface, hairline border, deep shadow.
 *  Two background colours per screen — the page and this.
 *
 * ⚠️ **The padding is a prop, not a class you pass in.** It used to be
 * `<Card className="p-0">`, and that silently did nothing: Tailwind resolves a
 * conflict between two padding utilities by their order in the stylesheet, not
 * by their order in the attribute, and `p-4` is emitted after `p-0`. The two
 * lists of movements carried a full card's padding for weeks because of it.
 * A prop cannot lose that argument — only one padding class is ever written.
 */

type Padding = 'none' | 'list' | 'normal'

const PADDINGS: Record<Padding, string> = {
  none: '',
  /** For a card that is a list of rows: the rows bring their own padding, and
   *  four pixels is just enough to keep them off the rounded corners. */
  list: 'p-1',
  /** ⚠️ Sixteen on a phone, twenty from `sm`. Twenty everywhere looked right in
   *  a desktop mock and wasted a tenth of a 390px screen on the device this app
   *  is actually used on. */
  normal: 'p-4 sm:p-5',
}

export function Card({
  children,
  className = '',
  padding = 'normal',
}: {
  children: ReactNode
  className?: string
  padding?: Padding
}) {
  return (
    <section
      className={`rounded-card border border-border-soft bg-surface-card shadow-card ${PADDINGS[padding]} ${className}`}
    >
      {children}
    </section>
  )
}
