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
      {/* ⚠️ The air in this row was never the padding — it was the leading.
          The type scale gives body 15/22 and caption 13/18: two lines of text
          are forty pixels tall for about twenty-eight pixels of letters, and no
          amount of squeezing the padding touches those twelve. So the two lines
          are set tight here, 20 and 16, and the padding stays at a comfortable
          twelve. Same row, four pixels shorter, and it reads far tighter
          because the two lines now belong to each other.
          A deliberate departure from the scale, recorded in DESIGN.md: this is
          the one place in the app where two lines of text are one object. */}
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-2.5 px-3.5 py-3 text-left transition-colors duration-200 hover:bg-surface-hover sm:gap-3 sm:px-5"
      >
        <Badge movement={movement} />

        <div className="min-w-0 flex-1">
          <p className="truncate text-body leading-5 text-ink-1">{title(movement)}</p>
          <p className="truncate text-caption leading-4 text-ink-2">{subtitle(movement)}</p>
        </div>

        <div className="shrink-0 text-right">
          <p className={`num text-body leading-5 ${amountClasses(movement)}`}>
            {amount(movement)}
          </p>
          {future ? <p className="text-micro uppercase leading-4 text-ink-3">futuro</p> : null}
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
        className="grid size-9 shrink-0 place-items-center rounded-control bg-money-transfer/15 text-money-transfer"
        aria-hidden
      >
        <ArrowLeftRight size={18} strokeWidth={2} />
      </span>
    )
  }

  if (movement.is_adjustment) {
    return (
      <span
        className="grid size-9 shrink-0 place-items-center rounded-control bg-money-adjustment/15 text-money-adjustment"
        aria-hidden
      >
        <Scale size={18} strokeWidth={2} />
      </span>
    )
  }

  return (
    <CategoryIcon
      icon={movement.category_icon ?? 'Ellipsis'}
      color={movement.category_color ?? 'chart-1'}
      box="sm"
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
