import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { setCacheOwner } from '../../api/cache'
import { api, type CurrentUser } from '../../api/client'

/** Who is signed in, asked once at startup and kept in context.
 *
 * The session itself lives in an httpOnly cookie the JavaScript cannot read, so
 * "am I signed in?" is a question only the server can answer: /api/auth/me is
 * the single source of truth, and `null` means no.
 */

interface SessionValue {
  user: CurrentUser | null
  loading: boolean
  setUser: (user: CurrentUser | null) => void
  refresh: () => Promise<void>
}

const SessionContext = createContext<SessionValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  // ⚠️ The read cache keeps accounts and categories on disk between sessions,
  // so it has to be told whose they are. A different id — or none — drops them:
  // a cache that outlives its session would hand one person's data to whoever
  // opens the app next.
  useEffect(() => {
    setCacheOwner(user?.id ?? null)
  }, [user?.id])

  const refresh = useCallback(async () => {
    try {
      setUser(await api.me())
    } catch {
      // A 401 is the normal answer for "not signed in"; a network failure is
      // not a logout either. Keeping whoever we had is the safe reading.
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <SessionContext.Provider value={{ user, loading, setUser, refresh }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext)
  if (!value) {
    throw new Error('useSession va usato dentro SessionProvider')
  }
  return value
}
