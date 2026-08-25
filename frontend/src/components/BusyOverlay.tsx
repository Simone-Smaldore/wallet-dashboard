import { useBusy } from '../api/busy'

/** Blocks the page while a foreground request is outstanding.
 *
 * Only after 200 ms (see useBusy): a flash of "attendi" on a 60 ms save reads
 * as a glitch rather than as feedback.
 *
 * The spinner is the one exception to a design that otherwise avoids motion —
 * a still image cannot say "I am working", and a frozen overlay reads as a
 * crash.
 */
export function BusyOverlay() {
  const busy = useBusy()
  if (!busy) return null

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-scrim"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3 rounded-pill border border-border-soft bg-surface-card px-5 py-3 shadow-card">
        <span className="size-4 animate-spin rounded-pill border-2 border-border-strong border-t-accent" />
        <span className="text-body text-ink-1">Attendi…</span>
      </div>
    </div>
  )
}
