import { WifiOff } from 'lucide-react'

import { useOnline } from '../lib/online'

/** The band that says there is no network.
 *
 * ⚠️ It says what it means for *you*, not what is true about the device. "Sei
 * senza rete" on its own leaves someone to discover by themselves that the
 * spend they just typed did not save. The second half of the sentence is the
 * whole reason the band exists.
 *
 * ⚠️ And it does not offer to save anything for later. Offline entry was
 * considered for V1 and dropped — a local queue is the most delicate piece in
 * the project — so promising it here would be a lie told by an interface.
 *
 * Sits under the fixed header on a phone and at the top of the page on a
 * desktop, above everything else the app draws.
 */
export function OfflineBanner() {
  const online = useOnline()
  if (online) return null

  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-40 flex items-center justify-center gap-2 bg-warn/15 px-4 py-2 text-center backdrop-blur-md sm:left-[212px]"
    >
      <WifiOff size={16} strokeWidth={2} className="shrink-0 text-warn" aria-hidden />
      <p className="text-caption text-ink-1">
        Sei senza rete: quello che registri adesso non viene salvato.
      </p>
    </div>
  )
}
