import { useState } from 'react'
import type { FormEvent } from 'react'

import { api, ACCOUNT_KINDS, type Account, type AccountKind } from '../../api/client'
import { Button } from '../../components/Button'
import { Field } from '../../components/Field'
import { Sheet } from '../../components/Sheet'
import { formatMoney, parseAmountField } from '../../lib/money'

export const KIND_LABELS: Record<AccountKind, string> = {
  corrente: 'Conto corrente',
  deposito: 'Conto deposito',
  contante: 'Contante',
  prepagata: 'Prepagata',
}

export function AccountForm({
  account,
  onClose,
  onSaved,
}: {
  account: Account | null
  onClose: () => void
  onSaved: () => void
}) {
  const editing = account !== null

  const [name, setName] = useState(account?.name ?? '')
  const [kind, setKind] = useState<AccountKind>(account?.kind ?? 'corrente')
  // ⚠️ Held as a string while it is being typed and converted only on save.
  // Never bound to a number input: emptying one turns the value into 0 and it
  // refills itself, so it could only be changed with the arrows.
  const [balance, setBalance] = useState(
    account ? formatMoney(account.opening_balance_cents, { symbol: false }) : '',
  )
  const [openingDate, setOpeningDate] = useState(
    account?.opening_date ?? new Date().toISOString().slice(0, 10),
  )
  const [counted, setCounted] = useState(account?.include_in_net_worth ?? true)

  const [amountError, setAmountError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    // An empty opening balance means zero here, and only here: you can open an
    // account you have not put anything into yet.
    const amount = parseAmountField(balance, { allowEmpty: true })
    if (amount.cents === null) {
      setAmountError(amount.error)
      return
    }
    setAmountError(null)
    const openingBalanceCents = amount.cents

    setSaving(true)
    try {
      const body = {
        name: name.trim(),
        kind,
        opening_balance_cents: openingBalanceCents,
        opening_date: openingDate,
        include_in_net_worth: counted,
      }
      if (editing) await api.updateAccount(account.id, body)
      else await api.createAccount(body)
      onSaved()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile salvare')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Sheet title={editing ? 'Modifica conto' : 'Nuovo conto'} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field
          label="Nome"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Conto corrente"
          autoFocus
          required
        />

        <div className="flex flex-col gap-1.5">
          <span className="text-caption text-ink-2">Tipo</span>
          <div className="flex flex-wrap gap-2">
            {ACCOUNT_KINDS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setKind(option)}
                className={[
                  'min-h-9 rounded-pill border px-3 text-caption transition-colors duration-200',
                  option === kind
                    ? 'border-accent bg-accent-dim text-accent'
                    : 'border-border-soft text-ink-2 hover:bg-surface-hover',
                ].join(' ')}
              >
                {KIND_LABELS[option]}
              </button>
            ))}
          </div>
        </div>

        <Field
          label="Saldo iniziale"
          value={balance}
          onChange={(event) => {
            setBalance(event.target.value)
            setAmountError(null)
          }}
          placeholder="0,00"
          inputMode="decimal"
          hint="Da qui in poi il saldo si calcola dai movimenti."
          error={amountError}
        />

        <Field
          label="Da quando"
          type="date"
          value={openingDate}
          onChange={(event) => setOpeningDate(event.target.value)}
        />

        <label className="flex items-start gap-3 rounded-control border border-border-soft p-3">
          <input
            type="checkbox"
            checked={counted}
            onChange={(event) => setCounted(event.target.checked)}
            className="mt-0.5 size-4 accent-[var(--color-accent)]"
          />
          <span className="text-body text-ink-1">
            Conta nel patrimonio
            <span className="mt-0.5 block text-caption text-ink-2">
              Toglilo per un conto cointestato o per soldi che tieni per qualcun altro. Le
              spese fatte da qui restano comunque nelle statistiche.
            </span>
          </span>
        </label>

        {error ? <p className="text-caption text-danger">{error}</p> : null}

        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? 'Salvo…' : 'Salva'}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Annulla
          </Button>
        </div>
      </form>
    </Sheet>
  )
}
