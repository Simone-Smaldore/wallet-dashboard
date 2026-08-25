import type { CategorySlice } from '../../api/client'
import { CategoryIcon } from '../CategoryIcon'
import { formatMoney, formatShare, formatSigned } from '../../lib/money'

/** Spending by category: horizontal bars, biggest first.
 *
 * ⚠️ Not a Recharts chart, and not for lack of trying. This needs a name, an
 * amount, a share and a change on every row, each one legible on a 390px
 * screen, and every row has to be pressable. That is a list with a bar in it,
 * not a plot — Recharts would be a library fought with rather than used, and
 * the labels would be the first thing to be truncated on a phone.
 *
 * ⚠️ **Every slice opens.** A number you cannot open is a number you will not
 * trust, and the first instinct in front of "Trasporti 340 €" is "and where
 * does that come from?".
 *
 * ⚠️ The change is shown in neutral ink, not in red or green. The app describes
 * and does not prescribe: spending 120 € more on transport than last month is a
 * fact, and whether it is bad news is not the app's call.
 */
export function CategoryBars({
  slices,
  onOpen,
}: {
  slices: CategorySlice[]
  onOpen: (slice: CategorySlice) => void
}) {
  return (
    <ul className="flex flex-col">
      {slices.map((slice) => (
        <li key={slice.category_id ?? 'none'}>
          <button
            type="button"
            onClick={() => onOpen(slice)}
            className="flex w-full items-center gap-3 rounded-control px-2 py-2.5 text-left transition-colors duration-200 hover:bg-surface-hover"
          >
            <CategoryIcon
              icon={slice.icon ?? 'Ellipsis'}
              color={slice.color ?? 'chart-1'}
              size={18}
            />

            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-3">
                <p className="min-w-0 truncate text-body text-ink-1">{slice.name}</p>
                <p className="num shrink-0 text-body text-ink-1">
                  {formatMoney(slice.total_cents)}
                </p>
              </div>

              <div className="mt-1.5 flex items-center gap-3">
                <Bar share={slice.share_permille} color={slice.color} />
                <p className="num w-14 shrink-0 text-right text-caption text-ink-3">
                  {formatShare(slice.share_permille)}
                </p>
              </div>

              {slice.previous_cents > 0 || slice.total_cents === 0 ? (
                <p className="num mt-1 text-caption text-ink-3">
                  {formatSigned(slice.delta_cents)} rispetto al periodo precedente
                </p>
              ) : null}
            </div>
          </button>
        </li>
      ))}
    </ul>
  )
}

function Bar({ share, color }: { share: number; color: string | null }) {
  return (
    <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-pill bg-surface-card-2">
      <span
        className="block h-full rounded-pill"
        style={{
          // The width is data, so it is the one thing here that cannot be a
          // class; the colour still comes from a token and nowhere else.
          width: `${Math.max(share / 10, share > 0 ? 1.5 : 0)}%`,
          background: color ? `var(--color-${color})` : 'var(--color-chart-axis)',
        }}
      />
    </span>
  )
}
