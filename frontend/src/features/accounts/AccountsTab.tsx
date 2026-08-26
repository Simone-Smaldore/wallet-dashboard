import { useState } from 'react'
import { Archive, ArchiveRestore, Pencil, Plus, Scale } from 'lucide-react'

import { api, type Account, type Asset } from '../../api/client'
import { useQuery } from '../../api/cache'
import { Amount } from '../../components/Amount'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { EmptyState } from '../../components/EmptyState'
import { AccountIcon } from '../../components/AccountIcon'
import { IconButton } from '../../components/IconButton'
import { formatMoney } from '../../lib/money'
import { formatDayShort } from '../../lib/period'
import { AccountForm, KIND_LABELS } from './AccountForm'
import { AssetForm } from './AssetForm'
import { BuySheet } from './BuySheet'
import { ReconcileSheet } from './ReconcileSheet'

export function AccountsTab() {
  // ⚠️ `fromDisk` is true while these came back from a previous session's
  // localStorage. The names are safe to show — they are labels. The balances
  // are not, and every amount below is held at a dash until the fresh copy
  // lands: see components/Amount.tsx.
  const { data, loading, fromDisk, error, refetch } = useQuery(
    '/api/accounts',
    api.accounts,
  )
  const [editing, setEditing] = useState<Account | null>(null)
  const [creating, setCreating] = useState(false)
  const [reconciling, setReconciling] = useState<Account | null>(null)
  const [editingAsset, setEditingAsset] = useState<{ asset: Asset | null; account: number } | null>(
    null,
  )
  const [buying, setBuying] = useState<Asset | null>(null)

  const assets = useQuery('/api/assets', api.assets)

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
  // Nothing at all yet — not even a remembered copy.
  const empty = loading && !data

  return (
    <div className="flex flex-col gap-3">
      <Card>
        <p className="text-micro uppercase text-ink-3">Patrimonio</p>
        <p className="mt-1 text-hero text-ink-1">
          <Amount cents={data?.net_worth_cents ?? 0} pending={fromDisk || empty} />
        </p>
        {data && data.invested_cents > 0 ? (
          <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
            <div className="flex items-baseline gap-2">
              <dt className="text-caption text-ink-2">Liquido</dt>
              <dd className="num text-body text-ink-1">{formatMoney(data.liquid_cents)}</dd>
            </div>
            <div className="flex items-baseline gap-2">
              <dt className="text-caption text-ink-2">Investito</dt>
              <dd className="num text-body text-ink-1">
                {formatMoney(data.invested_cents)}
              </dd>
            </div>
          </dl>
        ) : null}
        <p className="mt-1 text-caption text-ink-2">
          Somma dei conti che contano nel patrimonio.
          {data?.valued_on ? ` Investimenti valutati al ${formatDayShort(data.valued_on)}.` : ''}
        </p>
      </Card>

      {empty ? null : accounts.length === 0 ? (
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
              pending={fromDisk}
              assets={(assets.data ?? []).filter((a) => a.account_id === account.id)}
              onEdit={() => setEditing(account)}
              onReconcile={() => setReconciling(account)}
              onAddAsset={() => setEditingAsset({ asset: null, account: account.id })}
              onEditAsset={(asset) => setEditingAsset({ asset, account: account.id })}
              onBuyAsset={setBuying}
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
                pending={fromDisk}
                assets={[]}
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

      {buying ? <BuySheet asset={buying} onClose={() => setBuying(null)} /> : null}

      {editingAsset ? (
        <AssetForm
          asset={editingAsset.asset}
          accountId={editingAsset.account}
          onClose={() => setEditingAsset(null)}
        />
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
  pending,
  assets,
  onEdit,
  onReconcile,
  onAddAsset,
  onEditAsset,
  onBuyAsset,
}: {
  account: Account
  /** The name is remembered; the balance is not known yet. */
  pending: boolean
  assets: Asset[]
  onEdit: () => void
  onReconcile: () => void
  onAddAsset?: () => void
  onEditAsset?: (asset: Asset) => void
  onBuyAsset?: (asset: Asset) => void
}) {
  const investment = account.kind === 'investimento'
  // ⚠️ What it is worth comes from the server, not from adding up the assets
  // here. It was added up here first, and the Riepilogo — which has no asset
  // list — could not do the same, so it showed the capital instead. A number
  // shown on two screens is decided once.
  const worth = account.value_cents
  const gain = worth === null ? 0 : worth - account.balance_cents
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
        <AccountIcon kind={account.kind} />
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
        className={`text-title ${
          !pending && account.balance_cents < 0 ? 'text-money-expense' : 'text-ink-1'
        }`}
      >
        <Amount
          cents={investment && worth !== null ? worth : account.balance_cents}
          pending={pending}
        />
      </p>

      <p className="truncate text-caption text-ink-2">
        {KIND_LABELS[account.kind]}
        {account.include_in_net_worth ? '' : ' · fuori dal patrimonio'}
      </p>

      {investment ? (
        <>
          {worth !== null ? (
            <p className="text-caption text-ink-3">
              versato <span className="num">{formatMoney(account.balance_cents)}</span> ·{' '}
              <span className={`num ${gain < 0 ? 'text-money-expense' : 'text-money-income'}`}>
                {gain >= 0 ? '+' : '−'}
                {formatMoney(Math.abs(gain), { symbol: false })} €
              </span>
            </p>
          ) : (
            <p className="text-caption text-ink-3">
              Nessun prezzo: qui c'è il capitale versato.
            </p>
          )}

          <ul className="mt-1 flex flex-col gap-1 border-t border-border-soft pt-2">
            {assets.map((asset) => (
              <li key={asset.id}>
                <button
                  type="button"
                  onClick={() => onEditAsset?.(asset)}
                  className="flex w-full items-baseline justify-between gap-2 rounded-control px-1 py-0.5 text-left transition-colors duration-200 hover:bg-surface-hover"
                >
                  <span className="min-w-0 flex-1 truncate text-caption text-ink-2">
                    {asset.name}
                  </span>
                  <span className="num shrink-0 text-caption text-ink-1">
                    {asset.value_cents === null ? '—' : formatMoney(asset.value_cents)}
                  </span>
                </button>
                {/* ⚠️ The day the number was true, next to the number. Prices
                    come once a day and markets shut: a value that looks current
                    and is not is the one failure that matters here. */}
                <div className="flex items-baseline justify-between gap-2 px-1">
                  <p className="text-micro text-ink-3">
                    {asset.quantity}
                    {asset.valued_on ? ` · al ${formatDayShort(asset.valued_on)}` : ''}
                  </p>
                  {/* ⚠️ The monthly gesture, next to the thing it is about.
                      "Aggiungi" makes a new holding; this one grows an existing
                      one and records the money in the same breath. */}
                  {onBuyAsset ? (
                    <button
                      type="button"
                      onClick={() => onBuyAsset(asset)}
                      className="text-micro text-ink-3 transition-colors duration-200 hover:text-accent"
                    >
                      Ho comprato
                    </button>
                  ) : null}
                </div>
              </li>
            ))}

            {onAddAsset ? (
              <li>
                <button
                  type="button"
                  onClick={onAddAsset}
                  className="flex items-center gap-1 px-1 py-0.5 text-caption text-ink-3 transition-colors duration-200 hover:text-ink-1"
                >
                  <Plus size={13} strokeWidth={2} aria-hidden />
                  Aggiungi
                </button>
              </li>
            ) : null}
          </ul>
        </>
      ) : null}
    </li>
  )
}
