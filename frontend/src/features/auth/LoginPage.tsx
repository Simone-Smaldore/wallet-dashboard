import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Field } from '../../components/Field'
import { Wordmark } from '../../components/Wordmark'
import { isStandalone, tokenFromPaste } from '../../lib/pwa'
import { useSession } from './session'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!email.trim()) return

    setState('sending')
    try {
      await api.requestLink(email)
      setState('sent')
    } catch {
      setState('error')
    }
  }

  return (
    <div className="grid min-h-full place-items-center bg-bg-app px-4 py-10">
      <div className="flex w-full max-w-[400px] flex-col gap-3">
        <Wordmark />

        {state === 'sent' ? <LinkSent email={email} /> : null}

        {state !== 'sent' ? (
          <Card>
            <h1 className="font-display text-title text-ink-1">Entra</h1>
            <p className="mt-1 text-caption text-ink-2">
              Ti mandiamo un link via email. Niente password da ricordare.
            </p>

            <form onSubmit={submit} className="mt-5 flex flex-col gap-4">
              <Field
                label="Email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="la tua email"
                inputMode="email"
                autoComplete="email"
                autoFocus
                required
              />

              <Button type="submit" disabled={state === 'sending'}>
                {state === 'sending' ? 'Invio…' : 'Mandami il link'}
              </Button>

              {state === 'error' ? (
                <p className="text-caption text-danger">
                  Non è stato possibile inviare il link. Riprova fra poco.
                </p>
              ) : null}
            </form>
          </Card>
        ) : null}
      </div>
    </div>
  )
}

/** ⚠️ Says the same thing whatever happened.
 *
 * Allowed address, unknown address, rate limit: identical answer, because the
 * alternative is an endpoint that tells a stranger whose finances live here.
 */
function LinkSent({ email }: { email: string }) {
  return (
    <>
      <Card>
        <h1 className="font-display text-title text-ink-1">Controlla la posta</h1>
        <p className="mt-2 text-body text-ink-2">
          Se l'indirizzo è abilitato riceverai un link fra pochi istanti.
        </p>
        <p className="mt-3 text-caption text-ink-3">
          {email} · il link vale 15 minuti e si usa una volta sola
        </p>
      </Card>

      {isStandalone() ? <PasteLink /> : null}
    </>
  )
}

/** Only in the installed app, and only because of how iOS works.
 *
 * An app on the home screen has its own storage, so the link — which opens in
 * Safari — would create the session in the wrong place and leave this app
 * signed out, with no address bar to fix it from. Pasting the link spends the
 * token here instead.
 *
 * The instruction to copy rather than open matters: the token is single-use, so
 * whoever taps it first wins, and that would be Safari.
 */
function PasteLink() {
  const navigate = useNavigate()
  const { setUser } = useSession()
  const [value, setValue] = useState('')
  const [state, setState] = useState<'idle' | 'working' | 'error'>('idle')

  async function submit(event: FormEvent) {
    event.preventDefault()
    const token = tokenFromPaste(value)
    if (!token) {
      setState('error')
      return
    }

    setState('working')
    try {
      setUser(await api.verify(token))
      void navigate('/riepilogo', { replace: true })
    } catch {
      setState('error')
    }
  }

  return (
    <Card>
      <h2 className="font-display text-heading text-ink-1">
        Hai aperto l'app dalla schermata home?
      </h2>
      <p className="mt-1.5 text-caption text-ink-2">
        Nella mail tieni premuto il link e scegli Copia — non aprirlo, si usa una volta
        sola. Poi incollalo qui.
      </p>

      <form onSubmit={submit} className="mt-4 flex flex-col gap-4">
        <Field
          label="Link ricevuto per email"
          value={value}
          onChange={(event) => {
            setValue(event.target.value)
            setState('idle')
          }}
          placeholder="incolla il link"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          error={
            state === 'error' ? 'Questo link non è valido, o è già stato usato.' : null
          }
        />

        <Button type="submit" disabled={state === 'working'}>
          {state === 'working' ? 'Entro…' : 'Entra'}
        </Button>
      </form>
    </Card>
  )
}
