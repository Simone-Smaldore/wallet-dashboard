/** Tracks requests the user is actually waiting on.
 *
 * Kept apart from client.ts so nothing has to import React to make a request.
 *
 * "Actually waiting on" is doing work here: a request marked `quiet` — the
 * startup check for a session, the /_stato probe — is deliberately not counted.
 * Blocking the page for something nobody asked for is worse than showing
 * nothing.
 */

import { useEffect, useState } from 'react'

let inFlight = 0
const listeners = new Set<(busy: boolean) => void>()

function publish(): void {
  const busy = inFlight > 0
  for (const listener of listeners) listener(busy)
}

export function startRequest(): void {
  inFlight += 1
  publish()
}

export function endRequest(): void {
  inFlight = Math.max(0, inFlight - 1)
  publish()
}

/**
 * Hold the overlay up for the whole of an operation, not just its request.
 *
 * The counter is a counter and not a flag because these nest: a screen can wait
 * on two things at once, and the overlay must lift when the last one lands.
 */
export async function busyWhile<T>(run: () => Promise<T>): Promise<T> {
  startRequest()
  try {
    return await run()
  } finally {
    endRequest()
  }
}

/**
 * True while at least one foreground request is outstanding.
 *
 * `delayMs` keeps the overlay off the screen for requests that finish quickly:
 * a flash of "attendi" on a 60 ms save reads as a glitch, not as feedback. Only
 * a wait long enough to notice gets announced.
 */
export function useBusy(delayMs = 200): boolean {
  const [busy, setBusy] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    listeners.add(setBusy)
    return () => {
      listeners.delete(setBusy)
    }
  }, [])

  useEffect(() => {
    if (!busy) {
      // A short grace period before lifting: an operation that finishes and
      // immediately starts a follow-up would otherwise blink the overlay off
      // and straight back on.
      const timer = setTimeout(() => setVisible(false), SETTLE_MS)
      return () => clearTimeout(timer)
    }
    const timer = setTimeout(() => setVisible(true), delayMs)
    return () => clearTimeout(timer)
  }, [busy, delayMs])

  return visible
}

const SETTLE_MS = 80
