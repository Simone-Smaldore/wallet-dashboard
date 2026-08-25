import { useState } from 'react'
import type { FormEvent } from 'react'
import { Check, Plus, Trash2 } from 'lucide-react'

import { useQuery } from '../../api/cache'
import {
  api,
  type Category,
  type Transaction,
  type TransactionKind,
} from '../../api/client'
import { Button } from '../../components/Button'
import { CategoryIcon, categoryColorClasses } from '../../components/CategoryIcon'
import { Field } from '../../components/Field'
import { Sheet } from '../../components/Sheet'
import { useSession } from '../auth/session'
import { parseAmountField } from '../../lib/money'
import { formatMoney } from '../../lib/money'
import { isFuture, today } from '../../lib/period'

/** Recording a movement.
 *
 * ⚠️ This is the screen the app lives or dies on. CLAUDE.md: *a personal
 * finance app dies of friction at entry, not of missing features.* Amount,
 * category, save — everything else has a sensible default and stays out of the
 * way without being hidden.
 */
export function TransactionSheet({
  movement,
  onClose,
}: {
  movement: Transaction | null
  onClose: () => void
}) {
  const editing = movement !== null
  const { user, setUser } = useSession()

  const accounts = useQuery('/api/accounts', api.accounts)
  const categories = useQuery('/api/categories', api.categories)

  const [kind, setKind] = useState<TransactionKind>(movement?.kind ?? 'expense')
  const [amount, setAmount] = useState(
    movement ? formatMoney(movement.amount_cents, { symbol: false }) : '',
  )
  const [date, setDate] = useState(movement?.date ?? today())
  const [accountId, setAccountId] = useState<number | null>(
    movement?.account_id ?? lastAccountOf(user?.preferences),
  )
  const [counterId, setCounterId] = useState<number | null>(
    movement?.counter_account_id ?? null,
  )
  const [categoryId, setCategoryId] = useState<number | null>(movement?.category_id ?? null)
  const [description, setDescription] = useState(movement?.description ?? '')

  const [amountError, setAmountError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const openAccounts = (accounts.data?.accounts ?? []).filter((a) => !a.is_archived)
  const usable = (categories.data ?? []).filter(
    (category) =>
      !category.is_archived &&
      category.kind === (kind === 'income' ? 'income' : 'expense'),
  )

  // The account is preselected on the last one used, but only once the list has
  // arrived: picking the first of an empty list would silently change it.
  const chosenAccount = accountId ?? openAccounts[0]?.id ?? null

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    const parsed = parseAmountField(amount)
    if (parsed.cents === null) {
      setAmountError(parsed.error)
      return
    }
    setAmountError(null)

    if (chosenAccount === null) {
      setError('Serve almeno un conto: creane uno in Conti.')
      return
    }
    if (kind === 'transfer' && counterId === null) {
      setError('Scegli il conto di destinazione.')
      return
    }
    if (kind !== 'transfer' && categoryId === null) {
      setError('Scegli una categoria.')
      return
    }

    setSaving(true)
    try {
      const body = {
        kind,
        date,
        amount_cents: parsed.cents,
        account_id: chosenAccount,
        counter_account_id: kind === 'transfer' ? counterId : null,
        category_id: kind === 'transfer' ? null : categoryId,
        description: description.trim() || null,
      }
      if (editing) await api.updateTransaction(movement.id, body)
      else await api.createTransaction(body)

      // The server remembers the account used; keep the local copy in step so
      // the next sheet opens on it without a round trip.
      if (!editing && user) {
        setUser({ ...user, preferences: { ...user.preferences, last_account_id: chosenAccount } })
      }
      onClose()
    } catch (cause) {
      // ⚠️ The sheet stays open and stays full. The worst thing this screen can
      // do is make you type the amount again.
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile salvare')
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!editing) return
    setSaving(true)
    try {
      await api.deleteTransaction(movement.id)
      onClose()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Non è stato possibile cancellare')
      setSaving(false)
    }
  }

  return (
    <Sheet title={editing ? 'Modifica movimento' : 'Nuovo movimento'} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-5">
        <KindPicker
          value={kind}
          onChange={(next) => {
            setKind(next)
            // The category belongs to a sign: keeping it across a change would
            // file an expense under "Stipendio".
            setCategoryId(null)
            setError(null)
          }}
        />

        <div className="flex flex-col gap-1.5">
          <label htmlFor="importo" className="text-caption text-ink-2">
            Importo
          </label>
          <input
            id="importo"
            // ⚠️ text + inputMode, never type="number": emptying a number input
            // turns the value into 0 and it refills itself.
            type="text"
            inputMode="decimal"
            value={amount}
            onChange={(event) => {
              setAmount(event.target.value)
              setAmountError(null)
            }}
            placeholder="0,00"
            autoFocus
            className="num min-h-14 w-full rounded-control border border-border-soft bg-surface-input px-4 text-hero text-ink-1 placeholder:text-ink-3 focus:border-border-focus focus:outline-none"
          />
          {amountError ? <p className="text-caption text-danger">{amountError}</p> : null}
        </div>

        {kind === 'transfer' ? (
          <AccountPicker
            label="Verso"
            accounts={openAccounts.filter((account) => account.id !== chosenAccount)}
            value={counterId}
            onChange={setCounterId}
          />
        ) : (
          <CategoryPicker
            kind={kind === 'income' ? 'income' : 'expense'}
            categories={usable}
            value={categoryId}
            onChange={setCategoryId}
          />
        )}

        <AccountPicker
          label={kind === 'transfer' ? 'Da' : 'Conto'}
          accounts={openAccounts}
          value={chosenAccount}
          onChange={setAccountId}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Data"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            hint={isFuture(date) ? 'Data futura: conterà subito nel saldo.' : undefined}
          />
          <Field
            label="Descrizione"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="facoltativa"
          />
        </div>

        {error ? <p className="text-caption text-danger">{error}</p> : null}

        <div className="flex items-center gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? 'Salvo…' : 'Salva'}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Annulla
          </Button>
          {editing ? (
            <Button
              type="button"
              variant="danger"
              className="ml-auto"
              onClick={() => void remove()}
              disabled={saving}
            >
              <Trash2 size={18} strokeWidth={2} aria-hidden />
              Cancella
            </Button>
          ) : null}
        </div>
      </form>
    </Sheet>
  )
}

function lastAccountOf(preferences: Record<string, unknown> | undefined): number | null {
  const value = preferences?.last_account_id
  return typeof value === 'number' ? value : null
}

const KIND_LABELS: Record<TransactionKind, string> = {
  expense: 'Uscita',
  income: 'Entrata',
  transfer: 'Trasferimento',
}

/** ⚠️ A selector is right here: it picks a view of the same gesture, it does
 *  not hide different content behind a tab. */
function KindPicker({
  value,
  onChange,
}: {
  value: TransactionKind
  onChange: (kind: TransactionKind) => void
}) {
  const tones: Record<TransactionKind, string> = {
    expense: 'bg-money-expense/15 text-money-expense border-money-expense',
    income: 'bg-money-income/15 text-money-income border-money-income',
    transfer: 'bg-money-transfer/15 text-money-transfer border-money-transfer',
  }

  return (
    <div className="flex gap-2">
      {(Object.keys(KIND_LABELS) as TransactionKind[]).map((kind) => (
        <button
          key={kind}
          type="button"
          onClick={() => onChange(kind)}
          aria-pressed={kind === value}
          className={[
            'min-h-10 flex-1 rounded-pill border text-body transition-colors duration-200',
            kind === value
              ? tones[kind]
              : 'border-border-soft text-ink-2 hover:bg-surface-hover',
          ].join(' ')}
        >
          {KIND_LABELS[kind]}
        </button>
      ))}
    </div>
  )
}

function AccountPicker({
  label,
  accounts,
  value,
  onChange,
}: {
  label: string
  accounts: { id: number; name: string }[]
  value: number | null
  onChange: (id: number) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-caption text-ink-2">{label}</span>
      <div className="flex flex-wrap gap-2">
        {accounts.map((account) => (
          <button
            key={account.id}
            type="button"
            onClick={() => onChange(account.id)}
            aria-pressed={account.id === value}
            className={[
              'min-h-9 rounded-pill border px-3 text-caption transition-colors duration-200',
              account.id === value
                ? 'border-accent bg-accent-dim text-accent'
                : 'border-border-soft text-ink-2 hover:bg-surface-hover',
            ].join(' ')}
          >
            {account.name}
          </button>
        ))}
      </div>
    </div>
  )
}

/** The categories, plus the one that does not exist yet.
 *
 * ⚠️ Creating it here rather than sending someone to another section is the
 * difference between a category that fits and "Altro" forever. Only the name is
 * asked: the server picks a colour that is not already crowded and a neutral
 * icon, both changeable later in Categorie.
 */
function CategoryPicker({
  kind,
  categories,
  value,
  onChange,
}: {
  kind: 'expense' | 'income'
  categories: Category[]
  value: number | null
  onChange: (id: number) => void
}) {
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function create() {
    const trimmed = name.trim()
    if (!trimmed) return
    setSaving(true)
    setError(null)
    try {
      const created = await api.createCategory({ name: trimmed, kind })
      onChange(created.id)
      setCreating(false)
      setName('')
    } catch (cause) {
      // A duplicate name answers 409, and that answer is useful: if it already
      // exists, you did not need a new one.
      setError(cause instanceof Error ? cause.message : 'Non riesco a crearla')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-caption text-ink-2">Categoria</span>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {categories.map((category) => {
          const active = category.id === value
          const { text } = categoryColorClasses(category.color)
          return (
            <button
              key={category.id}
              type="button"
              onClick={() => onChange(category.id)}
              aria-pressed={active}
              className={[
                'flex flex-col items-center gap-1.5 rounded-control border p-2 transition-colors duration-200',
                active
                  ? `border-current ${text} bg-surface-hover`
                  : 'border-border-soft text-ink-2 hover:bg-surface-hover',
              ].join(' ')}
            >
              <CategoryIcon icon={category.icon} color={category.color} size={18} />
              <span className="w-full truncate text-center text-caption">{category.name}</span>
            </button>
          )
        })}

        <button
          type="button"
          onClick={() => setCreating(true)}
          className="flex flex-col items-center justify-center gap-1.5 rounded-control border border-dashed border-border-strong p-2 text-ink-2 transition-colors duration-200 hover:bg-surface-hover hover:text-ink-1"
        >
          <Plus size={18} strokeWidth={2} aria-hidden />
          <span className="text-caption">Nuova</span>
        </button>
      </div>

      {creating ? (
        <div className="mt-1 flex items-end gap-2">
          <div className="flex-1">
            <Field
              label="Nome della nuova categoria"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                setError(null)
              }}
              placeholder="Parrucchiere"
              autoFocus
              error={error}
              hint="Colore e icona li scegli dopo, in Categorie."
            />
          </div>
          <Button type="button" onClick={() => void create()} disabled={saving}>
            <Check size={18} strokeWidth={2} aria-hidden />
          </Button>
        </div>
      ) : null}
    </div>
  )
}
