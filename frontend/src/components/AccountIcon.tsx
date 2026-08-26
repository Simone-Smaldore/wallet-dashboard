import { Banknote, CreditCard, Landmark, PiggyBank, TrendingUp } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type { AccountKind } from '../api/client'

/** An account's badge: an icon in a tint, in a square container.
 *
 * ⚠️ **Investments are the one kind that reads differently**, and they earn it:
 * everything about them behaves unlike the others — paying in is a transfer,
 * the balance is capital rather than money, and the headline number comes from
 * a price feed. A list where they look identical to a current account invites
 * exactly the confusion the whole model exists to prevent.
 *
 * They take `--chart-3`, which is a token like any other, and the rest take
 * muted ink. ⚠️ Not the accent: that belongs to the primary action and the FAB
 * and does not get spread around. Not one of the four money colours either —
 * those mean income, spending, transfer and adjustment, and a fifth meaning
 * would blunt all four.
 *
 * Square, like a transfer's badge: round containers belong to categories.
 */

const ICONS: Record<AccountKind, LucideIcon> = {
  corrente: Landmark,
  deposito: PiggyBank,
  contante: Banknote,
  prepagata: CreditCard,
  investimento: TrendingUp,
}

export function AccountIcon({ kind, size = 18 }: { kind: AccountKind; size?: number }) {
  const Icon = ICONS[kind] ?? Landmark
  const investment = kind === 'investimento'

  return (
    <span
      className={[
        'grid size-8 shrink-0 place-items-center rounded-control',
        investment ? 'bg-chart-3/15 text-chart-3' : 'bg-surface-card-2 text-ink-3',
      ].join(' ')}
      aria-hidden
    >
      <Icon size={size} strokeWidth={2} />
    </span>
  )
}
