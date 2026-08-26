/** Whether there is a network, and a hook to watch it.
 *
 * ⚠️ `navigator.onLine` answers a narrower question than it looks: it means
 * "this device has some network interface up", not "the server is reachable".
 * A phone on a captive wifi portal reports itself online. So this is used for
 * exactly one thing — telling someone their writes will not land right now —
 * and never to decide whether to *attempt* a request. The request is the real
 * test, and it is always made.
 */

import { useEffect, useState } from 'react'

export function isOnline(): boolean {
  // Undefined in an environment without a navigator; assume connected, because
  // the failure mode of guessing "offline" is a banner nobody can dismiss.
  return typeof navigator === 'undefined' || navigator.onLine !== false
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(isOnline)

  useEffect(() => {
    const update = () => setOnline(isOnline())
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    // The state can have changed between the first render and this effect.
    update()
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  return online
}
