import { useState } from 'react'
import type { FormEvent } from 'react'

import { useQuery } from '../../api/cache'
import { api, type Account } from '../../api/client'
import { Button } from '../../components/Button'
import { Field } from '../../components/Field'
import { Sheet } from '../../components/Sheet'
import { formatMoney, parseAmountField } from '../../lib/money'
import { isFuture } from '../../lib/period'

/** "Il saldo vero oggi è X".
 *
 * The gesture for when the app and the bank disagree, which happens because a
 * spend went unrecorded. It writes a movement rather than editing the balance:
 * the balance is always `opening + Σ movements`, and a second number that can
 * disagree with the first is worse than one that takes a moment.
 */
export function ReconcileSheet({
  account,
  onClose,
}: {
  account: Account
  onClose: () => void
}) {
  const [balance, setBalance] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [amountError, setAmountError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState<{ difference: number } | null>(null)

  // Only to warn: the arithmetic happens server-side, where "today" is decided.
  const movements = useQuery(`/api/transactions?account_id=${account.id}`, () =>
    api.transactions({ account_id: account.id }),
  )
  const hasFuture = (movements.data?.transactions ?? []).some((row) => isFuture(row.date))

  async function submit(event: FormEvent) {
    event.preventDefault()
    const parsed = parseAmountField(balance)
    if (parsed.cents === null) {
      setAmountError(parsed.error)
      return
    }
    setAmountError(null)
    setError(null)
    setSaving(true)
    try {
      const result = await api.reconcile(account.id, parsed.cents)
      setDone({ difference: result.difference_cents })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile riconciliare')
    } finally {
      setSaving(false)
    }
  }

  if (done) {
    return (
      <Sheet title="Riconciliato" onClose={onClose}>
        <div className="flex flex-col gap-4">
          {done.difference === 0 ? (
            <p className="text-body text-ink-1">
              Il saldo era già giusto. Non ho scritto niente: un movimento da zero
              riempirebbe la lista senza dire nulla.
            </p>
          ) : (
            <p className="text-body text-ink-1">
              Mancavano{' '}
              <span className="num text-money-adjustment">
                {formatMoney(Math.abs(done.difference))}
              </span>
              . Ho registrato una rettifica{' '}
              {done.difference > 0 ? 'in entrata' : 'in uscita'} su {account.name}, senza
              categoria: non è una spesa, è la misura di quello che non avevi registrato.
            </p>
          )}
          <Button onClick={onClose}>Chiudi</Button>
        </div>
      </Sheet>
    )
  }

  return (
    <Sheet title={`Aggiorna il saldo di ${account.name}`} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="rounded-control border border-border-soft bg-surface-card-2 px-4 py-3">
          <p className="text-caption text-ink-2">Secondo l'app</p>
          <p className="num mt-0.5 text-title text-ink-1">
            {formatMoney(account.balance_cents)}
          </p>
        </div>

        <Field
          label="Secondo la banca, oggi"
          value={balance}
          onChange={(event) => {
            setBalance(event.target.value)
            setAmountError(null)
          }}
          placeholder="0,00"
          inputMode="decimal"
          autoFocus
          error={amountError}
          hint="La differenza diventa una rettifica, non una modifica del saldo iniziale."
        />

        {hasFuture ? (
          <p className="rounded-control bg-surface-card-2 px-3 py-2.5 text-caption text-ink-2">
            {/* ⚠️ The safeguard behind "future movements count in the balance".
                A statement cannot contain tomorrow, so the comparison stops at
                today — otherwise the difference would include money that has
                not moved and the rectification would be invented. */}
            Su questo conto ci sono movimenti con data futura. Il confronto li ignora: un
            estratto conto non può contenere domani.
          </p>
        ) : null}

        {error ? <p className="text-caption text-danger">{error}</p> : null}

        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? 'Calcolo…' : 'Riconcilia'}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Annulla
          </Button>
        </div>
      </form>
    </Sheet>
  )
}
