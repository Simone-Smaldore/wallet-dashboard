import { useState } from 'react'
import { Archive, ArchiveRestore, Pencil, Plus, Scale } from 'lucide-react'

import { api, type Account } from '../../api/client'
import { useQuery } from '../../api/cache'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { EmptyState } from '../../components/EmptyState'
import { IconButton } from '../../components/IconButton'
import { formatMoney } from '../../lib/money'
import { AccountForm, KIND_LABELS } from './AccountForm'
import { ReconcileSheet } from './ReconcileSheet'

export function AccountsTab() {
  const { data, loading, error, refetch } = useQuery('/api/accounts', api.accounts)
  const [editing, setEditing] = useState<Account | null>(null)
  const [creating, setCreating] = useState(false)
  const [reconciling, setReconciling] = useState<Account | null>(null)

  if (loading) return null
  if (error && !data) {
    return (
      <EmptyState title="Non riesco a leggere i conti">
        {error.message}
        <Button variant="secondary" onClick={refetch} className="mt-4">
          Riprova
        </Button>
      </EmptyState>
    )
  }

  const accounts = data?.accounts ?? []
  const active = accounts.filter((account) => !account.is_archived)
  const archived = accounts.filter((account) => account.is_archived)

  return (
    <div className="flex flex-col gap-3">
      <Card>
        <p className="text-micro uppercase text-ink-3">Patrimonio</p>
        <p className="num mt-1 text-hero text-ink-1">
          {formatMoney(data?.net_worth_cents ?? 0)}
        </p>
        <p className="mt-1 text-caption text-ink-2">
          Somma dei conti che contano nel patrimonio.
        </p>
      </Card>

      {accounts.length === 0 ? (
        <EmptyState title="Nessun conto">
          Comincia da dove tieni i soldi: il conto corrente, il deposito, il contante in
          tasca. Il saldo che scrivi qui è il punto da cui parte il conteggio.
        </EmptyState>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <h2 className="text-micro uppercase text-ink-3">I tuoi conti</h2>
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-caption text-ink-2 transition-colors duration-200 hover:bg-surface-hover hover:text-ink-1"
        >
          <Plus size={16} strokeWidth={2} aria-hidden />
          Nuovo conto
        </button>
      </div>

      {active.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {active.map((account) => (
            <AccountCard
              key={account.id}
              account={account}
              onEdit={() => setEditing(account)}
              onReconcile={() => setReconciling(account)}
            />
          ))}
        </ul>
      ) : null}

      {archived.length > 0 ? (
        <>
          <p className="mt-2 px-1 text-micro uppercase text-ink-3">Archiviati</p>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {archived.map((account) => (
              <AccountCard
                key={account.id}
                account={account}
                onEdit={() => setEditing(account)}
                onReconcile={() => setReconciling(account)}
              />
            ))}
          </ul>
        </>
      ) : null}

      {creating ? (
        <AccountForm
          account={null}
          onClose={() => setCreating(false)}
          onSaved={() => setCreating(false)}
        />
      ) : null}

      {editing ? (
        <AccountForm
          account={editing}
          onClose={() => setEditing(null)}
          onSaved={() => setEditing(null)}
        />
      ) : null}

      {reconciling ? (
        <ReconcileSheet account={reconciling} onClose={() => setReconciling(null)} />
      ) : null}
    </div>
  )
}

/** An account as a card.
 *
 * ⚠️ This started as a row and did not work. A row makes a column of amounts,
 * which is exactly right for a list of movements you scan looking for one — but
 * an account is not scanned, it is *read*: half a dozen of them, each a name and
 * a number that deserves to be legible. Squeezing name, type, balance and three
 * controls into 390 pixels of one line left nothing readable.
 *
 * So the rule in DESIGN.md is now narrower than "rows for money": **rows for
 * lists you scan, cards for a handful of things you read**.
 */
function AccountCard({
  account,
  onEdit,
  onReconcile,
}: {
  account: Account
  onEdit: () => void
  onReconcile: () => void
}) {
  async function toggleArchive() {
    // ⚠️ There is no delete. An account holds the history of its movements, and
    // the net-worth chart of two years ago runs through it.
    await api.updateAccount(account.id, { is_archived: !account.is_archived })
  }

  const archiveLabel = account.is_archived
    ? `Ripristina ${account.name}`
    : `Archivia ${account.name}`

  return (
    <li
      className={[
        'flex flex-col gap-2 rounded-card border border-border-soft bg-surface-card p-4 shadow-card',
        account.is_archived ? 'opacity-60' : '',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 flex-1 truncate text-body text-ink-1">{account.name}</p>

        {/* Pulled into the padding so the controls sit on the card's corner
            rather than stealing width from the name. */}
        <div className="-mr-1.5 -mt-1.5 flex shrink-0 items-center">
          {/* Where you reach when the number does not match the bank. */}
          <IconButton
            label={`Aggiorna il saldo di ${account.name}`}
            onClick={onReconcile}
            Icon={Scale}
          />
          <IconButton label={`Modifica ${account.name}`} onClick={onEdit} Icon={Pencil} />
          <IconButton
            label={archiveLabel}
            onClick={() => void toggleArchive()}
            Icon={account.is_archived ? ArchiveRestore : Archive}
          />
        </div>
      </div>

      {/* The number is what the card is for, so it gets the room. Red when
          negative: an account in the red is worth noticing without doing the
          arithmetic of reading a minus sign. */}
      <p
        className={`num text-title ${
          account.balance_cents < 0 ? 'text-money-expense' : 'text-ink-1'
        }`}
      >
        {formatMoney(account.balance_cents)}
      </p>

      <p className="truncate text-caption text-ink-2">
        {KIND_LABELS[account.kind]}
        {account.include_in_net_worth ? '' : ' · fuori dal patrimonio'}
      </p>
    </li>
  )
}
