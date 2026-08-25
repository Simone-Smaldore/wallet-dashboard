import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'

import { useQuery } from '../../api/cache'
import {
  api,
  type Category,
  type Transaction,
  type TransactionKind,
  type TransactionFilters,
} from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Dropdown } from '../../components/Dropdown'
import { IconButton } from '../../components/IconButton'
import { EmptyState } from '../../components/EmptyState'
import { formatDay, formatMonth, monthOf, shiftMonth, today } from '../../lib/period'
import { formatMoney } from '../../lib/money'
import { TransactionRow } from './TransactionRow'
import { TransactionSheet } from './TransactionSheet'

/** The list.
 *
 * Grouped by day with the day's spending on the header: you scroll looking for
 * "Tuesday", not reading twenty repeated dates, and the daily total comes for
 * free out of rows already on screen.
 */
export function TransactionsPage() {
  const [month, setMonth] = useState(() => today())
  const [kind, setKind] = useState<TransactionKind | ''>('')
  const [accountId, setAccountId] = useState<number | ''>('')
  const [categoryId, setCategoryId] = useState<number | ''>('')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<Transaction | null>(null)

  const period = monthOf(month)
  const filters: TransactionFilters = {
    from: period.start,
    to: period.end,
    ...(kind ? { kind } : {}),
    ...(accountId ? { account_id: accountId } : {}),
    ...(categoryId ? { category_id: categoryId } : {}),
    ...(search.trim() ? { q: search.trim() } : {}),
  }

  const key = `/api/transactions?${new URLSearchParams(
    Object.entries(filters).map(([k, v]) => [k, String(v)]),
  ).toString()}`

  const { data, loading, error } = useQuery(key, () => api.transactions(filters))

  const accounts = useQuery('/api/accounts', api.accounts)
  const categories = useQuery('/api/categories', api.categories)

  // Extra pages live outside the cache: a growing list is not a value to be
  // replaced, it is one being accumulated.
  const [extra, setExtra] = useState<Transaction[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    // A new filter is a new list: whatever had been paged in belonged to the
    // previous one.
    setExtra([])
    setCursor(data?.next_cursor ?? null)
  }, [key, data])

  async function loadMore() {
    if (!cursor) return
    setLoadingMore(true)
    try {
      const page = await api.transactions({ ...filters, cursor })
      setExtra((rows) => [...rows, ...page.transactions])
      setCursor(page.next_cursor)
    } finally {
      setLoadingMore(false)
    }
  }

  const movements = [...(data?.transactions ?? []), ...extra]
  const days = groupByDay(movements)

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-title text-ink-1">Movimenti</h1>

      <div className="flex items-center justify-between gap-2">
        <IconButton
          label="Mese precedente"
          onClick={() => setMonth(shiftMonth(month, -1))}
          Icon={ChevronLeft}
          size="md"
          iconSize={20}
        />
        <p className="text-body text-ink-1">{formatMonth(month)}</p>
        <IconButton
          label="Mese successivo"
          onClick={() => setMonth(shiftMonth(month, 1))}
          Icon={ChevronRight}
          size="md"
          iconSize={20}
        />
      </div>

      <div className="flex flex-col gap-2">
        <div className="relative">
          <Search
            size={18}
            strokeWidth={2}
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3"
          />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca nella descrizione"
            aria-label="Cerca"
            className="min-h-11 w-full rounded-control border border-border-soft bg-surface-input py-2 pl-10 pr-4 text-body text-ink-1 placeholder:text-ink-3 focus:border-border-focus focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <Chips
            label="Tutti"
            value={kind}
            onChange={setKind}
            options={[
              { value: 'expense', label: 'Uscite' },
              { value: 'income', label: 'Entrate' },
              { value: 'transfer', label: 'Trasferimenti' },
            ]}
          />
          <Dropdown
            placeholder="Scegli conto"
            value={accountId === '' ? null : accountId}
            onChange={(id) => setAccountId(id ?? '')}
            groups={[
              {
                label: 'Conti',
                options: (accounts.data?.accounts ?? [])
                  .filter((account) => !account.is_archived)
                  .map((account) => ({ value: account.id, label: account.name })),
              },
            ]}
          />
          {/* ⚠️ Two groups, never one list: an expense category and an income
              one are different things, and a filter that mixes them invites
              filtering spending by "Stipendio". */}
          <Dropdown
            placeholder="Scegli categoria"
            value={categoryId === '' ? null : categoryId}
            onChange={(id) => setCategoryId(id ?? '')}
            groups={categoryGroups(categories.data ?? [])}
          />
        </div>
      </div>

      {loading ? null : error && !data ? (
        <EmptyState title="Non riesco a leggere i movimenti">{error.message}</EmptyState>
      ) : movements.length === 0 ? (
        <EmptyState title="Nessun movimento in questo periodo">
          {/* ⚠️ Said in words. An empty list is not the same claim as "you spent
              nothing", and a chart at zero would make it. */}
          Registra il primo con il bottone +, oppure cambia mese o filtri.
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-4">
          {days.map(({ day, rows, spent }) => (
            <div key={day} className="flex flex-col gap-2">
              <div className="flex items-baseline justify-between gap-3 px-1">
                <h2 className="text-micro uppercase text-ink-3">{formatDay(day)}</h2>
                {spent > 0 ? (
                  <p className="num text-caption text-ink-3">−{formatMoney(spent)}</p>
                ) : null}
              </div>
              <Card className="p-0">
                <ul className="divide-y divide-border-soft">
                  {rows.map((movement) => (
                    <TransactionRow
                      key={movement.id}
                      movement={movement}
                      onOpen={() => setEditing(movement)}
                    />
                  ))}
                </ul>
              </Card>
            </div>
          ))}

          {cursor ? (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={() => void loadMore()} disabled={loadingMore}>
                {loadingMore ? 'Carico…' : 'Carica altri'}
              </Button>
            </div>
          ) : null}
        </div>
      )}

      {editing ? (
        <TransactionSheet movement={editing} onClose={() => setEditing(null)} />
      ) : null}
    </div>
  )
}

type Day = { day: string; rows: Transaction[]; spent: number }

/** ⚠️ Only expenses go into the day's total.
 *
 * A transfer moves money without spending it, and an adjustment measures what
 * was forgotten rather than what was bought. Adding either would make a day
 * look worse than it was, in the number people glance at most. */
function groupByDay(movements: Transaction[]): Day[] {
  const days = new Map<string, Day>()

  for (const movement of movements) {
    const existing = days.get(movement.date) ?? { day: movement.date, rows: [], spent: 0 }
    existing.rows.push(movement)
    if (movement.kind === 'expense' && !movement.is_adjustment) {
      existing.spent += movement.amount_cents
    }
    days.set(movement.date, existing)
  }

  return [...days.values()]
}

/** Categories split by sign, archived ones left out of a filter that is about
 *  what you are looking at now. */
function categoryGroups(categories: Category[]) {
  const usable = categories.filter((category) => !category.is_archived)
  const toOption = (category: Category) => ({
    value: category.id,
    label: category.name,
    color: category.color,
  })

  return [
    { label: 'Uscite', options: usable.filter((c) => c.kind === 'expense').map(toOption) },
    { label: 'Entrate', options: usable.filter((c) => c.kind === 'income').map(toOption) },
  ].filter((group) => group.options.length > 0)
}

function Chips<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: T | ''
  onChange: (value: T | '') => void
  options: { value: T; label: string }[]
}) {
  const all = [{ value: '' as const, label }, ...options]
  return (
    <div className="flex gap-1.5">
      {all.map((option) => (
        <button
          key={option.value || 'all'}
          type="button"
          onClick={() => onChange(option.value as T | '')}
          aria-pressed={option.value === value}
          className={[
            'min-h-9 rounded-pill border px-3 text-caption transition-colors duration-200',
            option.value === value
              ? 'border-accent bg-accent-dim text-accent'
              : 'border-border-soft text-ink-2 hover:bg-surface-hover',
          ].join(' ')}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
