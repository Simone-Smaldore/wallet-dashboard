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

import { busyWhile } from './busy'

interface Entry {
  data: unknown
  storedAt: number
  /** True while what is on screen came off the disk and has not been refreshed. */
  fromDisk?: boolean
}

const entries = new Map<string, Entry>()
const listeners = new Set<() => void>()

/** How long a value is trusted without asking the server again.
 *
 * ⚠️ Thirty seconds is the window for **money**: balances and statistics change
 * with every movement, and a minute-old total is a total that can be wrong.
 */
const DEFAULT_STALE_MS = 30_000

/** Names change twice a year, so they are trusted for far longer.
 *
 * Safe because there is one person writing here and their own writes invalidate
 * the key from inside client.ts the moment they land: a long window can never
 * show you something you just changed yourself. */
const LABELS_STALE_MS = 5 * 60_000

function staleFor(key: string, given?: number): number {
  if (given !== undefined) return given
  return key === '/api/categories' ? LABELS_STALE_MS : DEFAULT_STALE_MS
}

/* ------------------------------------------------------------------ disk --
 *
 * ⚠️ Only two keys are ever written here, and what they hold is **names, not
 * amounts**. See `persistable` below and the note in client.ts.
 */

const DISK_PREFIX = 'wallet:cache:'
//: Bumped when the shape of what is stored changes, so an old page's data is
//: dropped rather than misread.
const DISK_VERSION = 1

/** Whose data is on the disk. Set from the session; null means "nobody yet". */
let owner: number | null = null

interface Stored {
  version: number
  owner: number
  storedAt: number
  data: unknown
}

/** ⚠️ The allow-list, and it is short on purpose.
 *
 * Accounts and categories are labels: a name, a colour, an icon. They are read
 * by nearly every screen — above all by the entry sheet, which is the
 * three-taps-at-the-till screen — they are tiny, and they change twice a year.
 * Keeping them across a reload is what makes the app open with its content
 * already on screen.
 *
 * Everything else stays in memory: movements are a list that grows and has its
 * own cursor, and /api/stats/* is nothing but amounts. Money read off a disk is
 * a number from yesterday shown with confidence, which this project treats as
 * worse than no number at all.
 */
const PERSISTED = ['/api/accounts', '/api/categories'] as const

function persistable(key: string): boolean {
  return (PERSISTED as readonly string[]).includes(key)
}

/** Say who is signed in, so the disk can be dropped if it belongs to someone else.
 *
 * ⚠️ A `null` here does **not** clear anything, and that is deliberate: at
 * startup nobody is signed in yet for the length of one request, and clearing
 * on that would wipe the disk a moment before the app got to use it — the whole
 * point, undone by a race. Signing out goes through `clearCache()`, which is
 * explicit and unambiguous.
 *
 * What does clear is a *different* person: a cache that outlives its session
 * would serve one person's data to the next one to open the app. Same rule the
 * service worker follows for /api.
 */
export function setCacheOwner(userId: number | null): void {
  if (userId === null) return

  if (owner !== null && owner !== userId) {
    entries.clear()
    clearDisk()
  }
  owner = userId
}

/** Read what the last session left, for the keys allowed to leave one.
 *
 * ⚠️ Runs at import, before anything renders and before the session is known,
 * and it **adopts the owner written on the disk**. That is what makes the app
 * open with its content already there instead of after a round trip.
 *
 * Safe, because nothing signed-in renders until /api/auth/me has answered: if
 * that answer is a different person, `setCacheOwner` throws all of this away
 * before any of it reaches a screen. If it is nobody, the login page is what
 * gets drawn.
 */
function hydrate(): void {
  if (typeof localStorage === 'undefined') return

  for (const key of PERSISTED) {
    if (entries.has(key)) continue

    try {
      const raw = localStorage.getItem(DISK_PREFIX + key)
      if (!raw) continue
      const stored = JSON.parse(raw) as Stored
      if (stored.version !== DISK_VERSION) continue
      if (owner !== null && stored.owner !== owner) continue

      owner = stored.owner
      entries.set(key, { data: stored.data, storedAt: stored.storedAt, fromDisk: true })
    } catch {
      // Unreadable, or storage is unavailable in this context. The value comes
      // from the network like it always could; nothing here is load-bearing.
    }
  }
}

hydrate()

function toDisk(key: string, data: unknown): void {
  if (!persistable(key) || owner === null || typeof localStorage === 'undefined') return
  try {
    const stored: Stored = { version: DISK_VERSION, owner, storedAt: Date.now(), data }
    localStorage.setItem(DISK_PREFIX + key, JSON.stringify(stored))
  } catch {
    // Full, or private browsing. Not worth interrupting anyone over.
  }
}

function clearDisk(): void {
  if (typeof localStorage === 'undefined') return
  try {
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith(DISK_PREFIX)) localStorage.removeItem(key)
    }
  } catch {
    /* nothing to do about it */
  }
}

/* ----------------------------------------------------------------- cache -- */

/** Put a value straight into the cache and tell everyone reading it.
 *
 * Used by mutations that already receive the new state in their response:
 * throwing it away and asking for it again costs a round trip and leaves a gap
 * where the request has finished but the screen still shows the old value. */
export function setCached(key: string, data: unknown): void {
  entries.set(key, { data, storedAt: Date.now() })
  toDisk(key, data)
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
 * one's accounts and balances straight out of memory. And now out of the disk
 * too, which survives closing the tab, so this matters more than it did. */
export function clearCache(): void {
  entries.clear()
  clearDisk()
  owner = null
  for (const notify of listeners) notify()
}

export interface QueryState<T> {
  data: T | undefined
  /** True only when there is nothing to show yet, so a spinner is warranted. */
  loading: boolean
  /** True while a background refresh runs over data already on screen. */
  refreshing: boolean
  /**
   * ⚠️ True while what is on screen was read off the disk and the fresh copy
   * has not landed yet.
   *
   * It exists so a screen can show the *names* it remembers and hold back the
   * *numbers* it does not: a balance from yesterday, printed with confidence,
   * is the one failure this project cares about most.
   */
  fromDisk: boolean
  error: Error | undefined
  refetch: () => void
}

export function useQuery<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  options: { staleMs?: number; blocking?: boolean } = {},
): QueryState<T> {
  const staleMs = staleFor(key ?? '', options.staleMs)
  const { blocking = false } = options

  const cached = key ? (entries.get(key) as Entry | undefined) : undefined
  const [data, setData] = useState<T | undefined>(cached?.data as T | undefined)
  const [loading, setLoading] = useState(key !== null && cached === undefined)
  const [refreshing, setRefreshing] = useState(false)
  const [fromDisk, setFromDisk] = useState(cached?.fromDisk === true)
  const [error, setError] = useState<Error | undefined>(undefined)

  // Kept in refs so changing the fetcher identity between renders — which it
  // does, being an inline closure — never re-triggers the effect on its own.
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const dataRef = useRef(data)
  dataRef.current = data

  const run = useCallback(
    (currentKey: string, hasData: boolean) => {
      if (hasData) setRefreshing(true)
      else setLoading(true)

      let cancelled = false

      // ⚠️ The overlay, when a screen asks for it, and **only on a first load**.
      // A read that has nothing to show yet leaves a blank page, and there the
      // scrim is the honest thing: it says the app is working. A background
      // revalidate has correct data already on screen, and blocking the page
      // over it would undo the whole point of the cache — the rule this file
      // has always had, now that a read can block at all.
      const load = () =>
        blocking && !hasData ? busyWhile(() => fetcherRef.current()) : fetcherRef.current()

      load()
        .then((result) => {
          entries.set(currentKey, { data: result, storedAt: Date.now() })
          toDisk(currentKey, result)
          if (cancelled) return
          setData(result)
          setFromDisk(false)
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
    },
    [],
  )

  useEffect(() => {
    if (key === null) {
      setData(undefined)
      setLoading(false)
      return
    }

    const entry = entries.get(key) as Entry | undefined

    if (entry) {
      setData(entry.data as T)
      setFromDisk(entry.fromDisk === true)
      setLoading(false)
      // ⚠️ A value off the disk is always revalidated, however fresh it looks:
      // it was written by a previous session and nothing here knows what
      // happened in between.
      if (!entry.fromDisk && Date.now() - entry.storedAt < staleMs) {
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
        setFromDisk(entry.fromDisk === true)
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

  return { data, loading, refreshing, fromDisk, error, refetch }
}
