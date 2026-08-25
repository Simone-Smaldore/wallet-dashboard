import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { api } from '../../api/client'
import { Card } from '../../components/Card'
import { Wordmark } from '../../components/Wordmark'
import { useSession } from './session'

/** Where the emailed link lands.
 *
 * The token is spent by the POST this page fires on mount, never by loading the
 * URL itself. Mail providers fetch links to scan them, and a GET that consumed
 * the token would let a scanner burn it before you ever clicked. Scanners do
 * not execute JavaScript, so the POST only happens for a real visit.
 */

export function ConfirmPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { setUser } = useSession()
  const [error, setError] = useState<string | null>(null)
  // React StrictMode runs effects twice in dev; without this guard the second
  // run would spend an already-spent token and report a false failure.
  const attempted = useRef(false)

  const token = params.get('token')

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true

    if (!token) {
      setError('Link non valido')
      return
    }

    api
      .verify(token)
      .then((user) => {
        setUser(user)
        void navigate('/riepilogo', { replace: true })
      })
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : 'Link non valido')
      })
  }, [token, setUser, navigate])

  return (
    <div className="grid min-h-full place-items-center bg-bg-app px-4 py-10">
      <div className="flex w-full max-w-[400px] flex-col gap-3">
        <Wordmark />
        <Card>
          {error === null ? (
            <>
              <h1 className="font-display text-title text-ink-1">Un attimo</h1>
              <p className="mt-1 text-caption text-ink-2">Ti sto facendo entrare.</p>
            </>
          ) : (
            <>
              <h1 className="font-display text-title text-ink-1">Link non valido</h1>
              <p className="mt-2 text-body text-ink-2">{error}</p>
              <p className="mt-4 text-caption">
                <Link to="/accedi" className="text-accent underline hover:text-accent-hover">
                  Chiedine uno nuovo
                </Link>
              </p>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
