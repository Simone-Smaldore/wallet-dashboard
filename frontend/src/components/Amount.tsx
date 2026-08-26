import { formatMoney, formatSigned } from '../lib/money'

/** An amount, or an honest dash while it is not known yet.
 *
 * ⚠️ **This is what keeps a stale balance off the screen.** Accounts and
 * categories survive a reload on disk so the app opens with its content already
 * there — but only their *names* do. A balance changes with every movement, and
 * one read off yesterday's disk and printed with confidence is the failure this
 * project cares about most: a wrong number you trust is worse than a missing
 * number you ask about.
 *
 * So while `pending` is true the name is on screen and the number is a dash.
 * It lasts a fraction of a second, and for that fraction the app says "I do not
 * know yet" instead of saying something that used to be true.
 */
export function Amount({
  cents,
  pending = false,
  signed = false,
  className = '',
}: {
  cents: number
  /** True while the value on screen is remembered rather than known. */
  pending?: boolean
  /** For numbers that are a change rather than a quantity. */
  signed?: boolean
  className?: string
}) {
  if (pending) {
    return (
      <span className={`num text-ink-3 ${className}`} aria-label="in caricamento">
        —
      </span>
    )
  }

  return (
    <span className={`num ${className}`}>
      {signed ? formatSigned(cents) : formatMoney(cents)}
    </span>
  )
}
