import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { MonthPoint } from '../../api/client'
import { AXIS, CURSOR, GRID, MONEY, axisProps, tickInterval } from '../../lib/chart'
import { formatMoney, formatMoneyShort, formatSigned } from '../../lib/money'
import { formatMonth, monthTick } from '../../lib/period'

/** Income and spending, month by month, diverging from a zero line.
 *
 * ⚠️ **One month is one column**, income growing up and spending down.
 *
 * It started as two bars side by side, and that was the wrong picture: with a
 * pair per month and a dozen months on screen, nothing tells you whether the
 * red bar you are looking at belongs to the green one on its left or the one on
 * its right. Reading it meant counting.
 *
 * Above and below a shared zero fixes that structurally instead of with a
 * label — and it is the more honest encoding anyway, because income and
 * spending are opposite in sense, not two sizes of the same thing. What is left
 * over at the axis *is* the month's saving, which is the question the chart
 * exists to answer.
 *
 * ⚠️ The axis shows both halves as positive numbers. A "−1,2k" under the line
 * would say the same thing twice — the side already carries the sign — and this
 * app never writes a negative amount.
 */
export function MonthlyBars({
  months,
  onSelect,
}: {
  months: MonthPoint[]
  onSelect?: (month: string) => void
}) {
  // Spending is drawn downwards. It stays positive everywhere else: the sign
  // here is a property of the drawing, not of the number.
  const data: Point[] = months.map((month) => ({
    ...month,
    outflow: -month.expense_cents,
  }))

  return (
    <div>
      <Legend />

      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart
          data={data}
          stackOffset="sign"
          margin={{ top: 4, right: 4, bottom: 0, left: -12 }}
          // Tight inside a month, loose between months: the eye groups what is
          // close together before it has read anything.
          barCategoryGap="22%"
          onClick={(state) => {
            // ⚠️ Every chart is a starting point: a month you can see is a month
            // you can open. Recharts hands back the index, not the datum.
            const index = state?.activeTooltipIndex
            if (onSelect && typeof index === 'number' && data[index]) {
              onSelect(data[index].month)
            }
          }}
        >
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey="month"
            tickFormatter={monthTick}
            interval={tickInterval(months.length)}
            {...axisProps}
          />
          <YAxis
            tickFormatter={(value: number) => formatMoneyShort(Math.abs(value))}
            width={64}
            {...axisProps}
          />
          <Tooltip cursor={CURSOR} content={<MonthTooltip />} />

          {/* The line the two halves grow from. Without it the bars float. */}
          <ReferenceLine y={0} stroke={AXIS} strokeWidth={1} />

          {/* One signed stack: same column, opposite directions. */}
          <Bar
            dataKey="income_cents"
            stackId="month"
            fill={MONEY.income}
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
          <Bar
            dataKey="outflow"
            stackId="month"
            fill={MONEY.expense}
            radius={[0, 0, 3, 3]}
            isAnimationActive={false}
          />

          {/* What was left over. A dot per month, because on a chart made of
              bars a bare line gives the eye nowhere to land. */}
          <Line
            type="monotone"
            dataKey="savings_cents"
            stroke="var(--color-ink-1)"
            strokeWidth={1.5}
            dot={{ r: 2, fill: 'var(--color-ink-1)', strokeWidth: 0 }}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** ⚠️ Written out rather than left to Recharts' own `<Legend>`.
 *
 * Three colours with no key is a chart you have to be told how to read. The
 * library's legend arrives with its own type, spacing and swatch shapes, and
 * restyling it into this design system costs more than saying it here. */
function Legend() {
  const items = [
    { label: 'Entrate', colour: MONEY.income, shape: 'size-2.5 rounded-[3px]' },
    { label: 'Uscite', colour: MONEY.expense, shape: 'size-2.5 rounded-[3px]' },
    { label: 'Differenza', colour: 'var(--color-ink-1)', shape: 'h-0.5 w-3 rounded-pill' },
  ]

  return (
    <ul className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span
            className={`shrink-0 ${item.shape}`}
            style={{ background: item.colour }}
            aria-hidden
          />
          <span className="text-caption text-ink-2">{item.label}</span>
        </li>
      ))}
    </ul>
  )
}

type Point = MonthPoint & { outflow: number }

function MonthTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload?: Point }>
}) {
  const month = payload?.[0]?.payload
  if (!active || !month) return null

  return (
    <div className="rounded-control border border-border-strong bg-bg-raise px-3 py-2 shadow-card">
      <p className="text-caption text-ink-2">{formatMonth(month.month)}</p>

      {month.movement_count === 0 ? (
        // ⚠️ Said in words. Three zeros would read as "you earned nothing and
        // spent nothing", which is a different claim from "nothing was
        // recorded".
        <p className="mt-1 text-caption text-ink-3">Nessun movimento</p>
      ) : (
        <ul className="mt-1 flex flex-col gap-0.5">
          <Row
            label="Entrate"
            value={formatMoney(month.income_cents)}
            tone="text-money-income"
          />
          <Row
            label="Uscite"
            value={formatMoney(month.expense_cents)}
            tone="text-money-expense"
          />
          <Row
            label="Differenza"
            value={formatSigned(month.savings_cents)}
            tone={month.savings_cents < 0 ? 'text-money-expense' : 'text-ink-1'}
          />
        </ul>
      )}
    </div>
  )
}

function Row({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <li className="flex items-baseline gap-4">
      <span className="flex-1 text-caption text-ink-2">{label}</span>
      <span className={`num text-caption ${tone}`}>{value}</span>
    </li>
  )
}
