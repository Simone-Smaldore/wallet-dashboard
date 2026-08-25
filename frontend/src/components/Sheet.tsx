import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'

import { IconButton } from './IconButton'

/** A panel that comes up from the bottom, over a scrim.
 *
 * Creating an account is three fields; it does not deserve a navigation, and a
 * sheet keeps the list you were reading visible behind it. Rounded at the top
 * only, per DESIGN.md.
 */
export function Sheet({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  // Escape closes it. A sheet with no way out but a small button is a trap on a
  // keyboard.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <button
        type="button"
        aria-label="Chiudi"
        onClick={onClose}
        className="absolute inset-0 bg-scrim"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative max-h-[90vh] w-full max-w-[480px] overflow-y-auto rounded-t-sheet border border-border-soft bg-bg-raise p-5 shadow-card sm:rounded-sheet"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-display text-heading text-ink-1">{title}</h2>
          <IconButton label="Chiudi" onClick={onClose} Icon={X} iconSize={20} />
        </div>

        {children}
      </div>
    </div>
  )
}
