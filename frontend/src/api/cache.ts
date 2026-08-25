/** A small stale-while-revalidate cache for GET requests.
 *
 * The problem it solves: leaving a list and coming back re-fetched everything
 * and flashed an empty screen, even though nothing had changed.
 *
 * How it behaves:
 *   - fresh entry -> returned immediately, no request at all;
 *   - stale entry -> returned immediately, refreshed quietly in the background;
 *   - nothing yet -> loading, then the result.
 *
 * Writes call `invalidate()` with a prefix from inside client.ts, so a caller
 * cannot forget to do it.
 *
 * Deliberately not TanStack Query. That library is better than this at retries,
 * pagination and de-duplication across components, and if the app ever grows
 * those needs it should replace this file wholesale. For a handful of endpoints
 * it would be more configuration than code.
 *
 * Deliberately smaller than its ancestor, too: no polling, no guards against
 * out-of-order optimistic writes, no offline store. That machinery exists in
 * the project this is modelled on to serve a shopping list two people tick at
 * the same time inside a supermarket. Here it would be apparatus without a
 * problem.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

interface Entry {
  data: unknown
  storedAt: number
}

const entries = new Map<string, Entry>()
const listeners = new Set<() => void>()

/** How long a value is trusted without asking the server again. */
const DEFAULT_STALE_MS = 30_000

/** Put a value straight into the cache and tell everyone reading it.
 *
 * Used by mutations that already receive the new state in their response:
 * throwing it away and asking for it again costs a round trip and leaves a gap
 * where the request has finished but the screen still shows the old value. */
export function setCached(key: string, data: unknown): void {
  entries.set(key, { data, storedAt: Date.now() })
  for (const notify of listeners) notify()
}

export function invalidate(prefix: string): void {
  for (const key of entries.keys()) {
    if (key.startsWith(prefix)) entries.delete(key)
  }
  for (const notify of listeners) notify()
}

/** ⚠️ Wipe everything — called on sign-out.
 *
 * Without this, the next person to sign in on this browser reads the previous
 * one's accounts and balances straight out of memory. */
export function clearCache(): void {
  entries.clear()
  for (const notify of listeners) notify()
}

export interface QueryState<T> {
  data: T | undefined
  /** True only when there is nothing to show yet, so a spinner is warranted. */
  loading: boolean
  /** True while a background refresh runs over data already on screen. */
  refreshing: boolean
  error: Error | undefined
  refetch: () => void
}

export function useQuery<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  options: { staleMs?: number } = {},
): QueryState<T> {
  const { staleMs = DEFAULT_STALE_MS } = options

  const cached = key ? (entries.get(key) as Entry | undefined) : undefined
  const [data, setData] = useState<T | undefined>(cached?.data as T | undefined)
  const [loading, setLoading] = useState(key !== null && cached === undefined)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<Error | undefined>(undefined)

  // Kept in refs so changing the fetcher identity between renders — which it
  // does, being an inline closure — never re-triggers the effect on its own.
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const dataRef = useRef(data)
  dataRef.current = data

  const run = useCallback((currentKey: string, hasData: boolean) => {
    if (hasData) setRefreshing(true)
    else setLoading(true)

    let cancelled = false

    fetcherRef
      .current()
      .then((result) => {
        entries.set(currentKey, { data: result, storedAt: Date.now() })
        if (cancelled) return
        setData(result)
        setError(undefined)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        // Keep whatever is already on screen: a failed refresh should not blank
        // a list that was perfectly good a second ago.
        setError(cause instanceof Error ? cause : new Error(String(cause)))
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
        setRefreshing(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (key === null) {
      setData(undefined)
      setLoading(false)
      return
    }

    const entry = entries.get(key) as Entry | undefined

    if (entry) {
      setData(entry.data as T)
      setLoading(false)
      if (Date.now() - entry.storedAt < staleMs) {
        return // Fresh enough. No request.
      }
    }

    return run(key, entry !== undefined)
  }, [key, staleMs, run])

  // Re-read when something invalidates the prefix this query lives under.
  useEffect(() => {
    if (key === null) return

    const notify = () => {
      const entry = entries.get(key) as Entry | undefined
      if (entry) {
        // A mutation pushed a fresh value in; take it, no request needed.
        setData(entry.data as T)
        return
      }
      // Invalidated. Refresh over whatever is on screen rather than blanking
      // it: a save should not flash an empty list.
      run(key, dataRef.current !== undefined)
    }
    listeners.add(notify)
    return () => {
      listeners.delete(notify)
    }
  }, [key, run])

  const refetch = useCallback(() => {
    if (key !== null) {
      entries.delete(key)
      run(key, data !== undefined)
    }
  }, [key, run, data])

  return { data, loading, refreshing, error, refetch }
}
