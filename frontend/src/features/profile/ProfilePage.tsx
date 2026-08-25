import { useState } from 'react'
import type { FormEvent } from 'react'
import { LogOut, ShieldOff } from 'lucide-react'
import { useNavigate } from 'react-router'

import { clearCache } from '../../api/cache'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Field } from '../../components/Field'
import { useSession } from '../auth/session'

export function ProfilePage() {
  const { user, setUser } = useSession()
  const navigate = useNavigate()
  const [name, setName] = useState(user?.display_name ?? '')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!user) return null

  async function save(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      // An empty box means "drop my name and show my email again", which is a
      // different instruction from not touching the field at all.
      const trimmed = name.trim()
      setUser(await api.updateProfile({ display_name: trimmed === '' ? null : trimmed }))
      setSaved(true)
    } catch {
      setError('Non è stato possibile salvare. Riprova.')
    }
  }

  async function leave(everywhere: boolean) {
    try {
      await (everywhere ? api.logoutAll() : api.logout())
    } finally {
      // Whatever the server said, this browser is done: keeping a stale user in
      // context would leave the app looking signed in while every call 401s.
      //
      // ⚠️ And the read cache goes with it. Without this the next person to
      // sign in on this browser reads the previous one's accounts and balances
      // straight out of memory.
      clearCache()
      setUser(null)
      void navigate('/accedi', { replace: true })
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-title text-ink-1">Profilo</h1>

      <Card>
        <form onSubmit={save} className="flex flex-col gap-4">
          <Field
            label="Nome"
            value={name}
            onChange={(event) => {
              setName(event.target.value)
              setSaved(false)
            }}
            placeholder={user.email}
            hint="Lascialo vuoto per farti chiamare con la tua email."
            autoComplete="name"
            error={error}
          />
          <div className="flex items-center gap-3">
            <Button type="submit">Salva</Button>
            {saved ? <span className="text-caption text-accent">Salvato</span> : null}
          </div>
        </form>
      </Card>

      <Card>
        <h2 className="font-display text-heading text-ink-1">Accesso</h2>
        <p className="mt-1 text-caption text-ink-2">
          Entri con {user.email}. La sessione dura 30 giorni e si rinnova a ogni uso.
        </p>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <Button variant="secondary" onClick={() => void leave(false)}>
            <LogOut size={18} strokeWidth={2} aria-hidden />
            Esci
          </Button>
          <Button variant="danger" onClick={() => void leave(true)}>
            <ShieldOff size={18} strokeWidth={2} aria-hidden />
            Esci da tutti i dispositivi
          </Button>
        </div>

        <p className="mt-3 text-caption text-ink-3">
          Il secondo è quello da usare se perdi il telefono: chiude ogni sessione aperta,
          ovunque.
        </p>
      </Card>
    </div>
  )
}
