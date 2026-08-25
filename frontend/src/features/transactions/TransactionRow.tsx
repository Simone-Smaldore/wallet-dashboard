import { ArrowLeftRight, Scale } from 'lucide-react'

import type { Transaction } from '../../api/client'
import { CategoryIcon } from '../../components/CategoryIcon'
import { formatMoney } from '../../lib/money'
import { isFuture } from '../../lib/period'

/** One movement.
 *
 * ⚠️ A transfer must not read like an expense. It is cyan, it carries **no
 * sign**, its title is `Conto → Conto` and its icon sits in a **square**
 * container while categories get a round one — the shape alone says which of
 * the two you are looking at. If this row reads wrong, the whole model is lost
 * in the one place the user actually looks.
 */
export function TransactionRow({
  movement,
  onOpen,
}: {
  movement: Transaction
  onOpen: () => void
}) {
  const future = isFuture(movement.date)

  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-3 px-5 py-3 text-left transition-colors duration-200 hover:bg-surface-hover"
      >
        <Badge movement={movement} />

        <div className="min-w-0 flex-1">
          <p className="truncate text-body text-ink-1">{title(movement)}</p>
          <p className="truncate text-caption text-ink-2">{subtitle(movement)}</p>
        </div>

        <div className="shrink-0 text-right">
          <p className={`num text-body ${amountClasses(movement)}`}>{amount(movement)}</p>
          {future ? <p className="text-micro uppercase text-ink-3">futuro</p> : null}
        </div>
      </button>
    </li>
  )
}

function Badge({ movement }: { movement: Transaction }) {
  if (movement.kind === 'transfer') {
    // Square, per DESIGN.md: the container shape distinguishes a transfer from
    // a category at a glance, before any colour is read.
    return (
      <span
        className="grid size-10 shrink-0 place-items-center rounded-control bg-money-transfer/15 text-money-transfer"
        aria-hidden
      >
        <ArrowLeftRight size={20} strokeWidth={2} />
      </span>
    )
  }

  if (movement.is_adjustment) {
    return (
      <span
        className="grid size-10 shrink-0 place-items-center rounded-control bg-money-adjustment/15 text-money-adjustment"
        aria-hidden
      >
        <Scale size={20} strokeWidth={2} />
      </span>
    )
  }

  return (
    <CategoryIcon
      icon={movement.category_icon ?? 'Ellipsis'}
      color={movement.category_color ?? 'chart-1'}
    />
  )
}

function title(movement: Transaction): string {
  if (movement.kind === 'transfer') {
    return `${movement.account_name} → ${movement.counter_account_name ?? '?'}`
  }
  return movement.description || movement.category_name || 'Senza categoria'
}

function subtitle(movement: Transaction): string {
  if (movement.kind === 'transfer') return 'Trasferimento'
  if (movement.is_adjustment) return `Rettifica · ${movement.account_name}`

  const parts = [movement.category_name, movement.account_name].filter(Boolean)
  // The description takes the title when it is there, so the category is not
  // lost — it moves down here.
  return parts.join(' · ')
}

function amount(movement: Transaction): string {
  const value = formatMoney(movement.amount_cents)
  if (movement.kind === 'transfer') return value
  return movement.kind === 'income' ? `+${value}` : `−${value}`
}

function amountClasses(movement: Transaction): string {
  if (movement.kind === 'transfer') return 'text-money-transfer'
  if (movement.is_adjustment) return 'text-money-adjustment'
  return movement.kind === 'income' ? 'text-money-income' : 'text-money-expense'
}
