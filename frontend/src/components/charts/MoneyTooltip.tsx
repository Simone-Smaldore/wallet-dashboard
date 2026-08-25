import { formatMoney } from '../../lib/money'
import { formatMonth } from '../../lib/period'

/** The tooltip, written rather than restyled.
 *
 * Recharts' own tooltip is a white box with a border, and reshaping it through
 * `contentStyle` means passing inline styles for something the design system
 * already describes: a card surface, a hairline border, a 12px radius. It is
 * also the only way to get amounts through `formatMoney` without fighting the
 * library's formatter types — which are wide enough to accept anything and
 * therefore assignable from almost nothing.
 *
 * ⚠️ Amounts here are whole, never the short axis form. A tooltip is where you
 * look to read the actual number.
 */

type Entry = {
  name?: string
  value?: number | string | Array<number | string>
  color?: string
  dataKey?: string | number
}

export function MoneyTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Entry[]
  label?: unknown
}) {
  if (!active || !payload || payload.length === 0) return null

  return (
    <div className="rounded-control border border-border-strong bg-bg-raise px-3 py-2 shadow-card">
      <p className="text-caption text-ink-2">{formatMonth(String(label))}</p>
      <ul className="mt-1 flex flex-col gap-0.5">
        {payload.map((entry) => (
          <li key={String(entry.dataKey)} className="flex items-baseline gap-3">
            <span
              className="size-2 shrink-0 rounded-pill"
              style={{ background: entry.color }}
              aria-hidden
            />
            <span className="flex-1 text-caption text-ink-2">{entry.name}</span>
            <span className="num text-caption text-ink-1">
              {formatMoney(Number(entry.value ?? 0))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
