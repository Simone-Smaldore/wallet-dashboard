import { useState } from 'react'
import { Archive, ArchiveRestore, Pencil, Plus } from 'lucide-react'

import { api, type Account } from '../../api/client'
import { useQuery } from '../../api/cache'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { EmptyState } from '../../components/EmptyState'
import { formatMoney } from '../../lib/money'
import { AccountForm, KIND_LABELS } from './AccountForm'

export function AccountsTab() {
  const { data, loading, error, refetch } = useQuery('/api/accounts', api.accounts)
  const [editing, setEditing] = useState<Account | null>(null)
  const [creating, setCreating] = useState(false)

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
          Somma dei conti che contano. Da M3 si muoverà con i movimenti.
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
        <Card className="p-0">
          {/* A list, not a grid: a column of amounts in the same place on every
              row is what makes them readable at a glance. Categories are tiles
              because a category is an icon and a word; a balance is a number. */}
          <ul>
            {active.map((account, index) => (
              <AccountRow
                key={account.id}
                account={account}
                first={index === 0}
                onEdit={() => setEditing(account)}
              />
            ))}
          </ul>
        </Card>
      ) : null}

      {archived.length > 0 ? (
        <>
          <p className="px-1 text-micro uppercase text-ink-3">Archiviati</p>
          <Card className="p-0">
            <ul>
              {archived.map((account, index) => (
                <AccountRow
                  key={account.id}
                  account={account}
                  first={index === 0}
                  onEdit={() => setEditing(account)}
                />
              ))}
            </ul>
          </Card>
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
    </div>
  )
}

function AccountRow({
  account,
  first,
  onEdit,
}: {
  account: Account
  first: boolean
  onEdit: () => void
}) {
  async function toggleArchive() {
    // ⚠️ There is no delete. An account holds the history of its movements, and
    // the net-worth chart of two years ago runs through it.
    await api.updateAccount(account.id, { is_archived: !account.is_archived })
  }

  return (
    <li
      className={[
        'flex items-center gap-3 px-5 py-4',
        first ? '' : 'border-t border-border-soft',
        account.is_archived ? 'opacity-60' : '',
      ].join(' ')}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-ink-1">{account.name}</p>
        <p className="truncate text-caption text-ink-2">
          {KIND_LABELS[account.kind]}
          {account.include_in_net_worth ? '' : ' · fuori dal patrimonio'}
        </p>
      </div>

      {/* Amounts live in the same place on every row, right aligned and
          tabular: that is what lets a column of them be read at a glance. */}
      <p className="num shrink-0 text-body text-ink-1">{formatMoney(account.balance_cents)}</p>

      <button
        type="button"
        onClick={onEdit}
        aria-label={`Modifica ${account.name}`}
        className="grid size-9 shrink-0 place-items-center rounded-pill text-ink-3 transition-colors duration-200 hover:bg-surface-hover hover:text-ink-1"
      >
        <Pencil size={18} strokeWidth={2} aria-hidden />
      </button>
      <button
        type="button"
        onClick={() => void toggleArchive()}
        aria-label={account.is_archived ? `Ripristina ${account.name}` : `Archivia ${account.name}`}
        className="grid size-9 shrink-0 place-items-center rounded-pill text-ink-3 transition-colors duration-200 hover:bg-surface-hover hover:text-ink-1"
      >
        {account.is_archived ? (
          <ArchiveRestore size={18} strokeWidth={2} aria-hidden />
        ) : (
          <Archive size={18} strokeWidth={2} aria-hidden />
        )}
      </button>
    </li>
  )
}
