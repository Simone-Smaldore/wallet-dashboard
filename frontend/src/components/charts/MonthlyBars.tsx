import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { MonthPoint } from '../../api/client'
import { AXIS, CURSOR, GRID, MONEY, axisProps, tickInterval } from '../../lib/chart'
import { formatMoneyShort } from '../../lib/money'
import { monthTick } from '../../lib/period'
import { MoneyTooltip } from './MoneyTooltip'

/** Income, spending and the difference, month by month.
 *
 * Two bars and a line rather than three bars: the difference is not a third
 * quantity of the same sort, it is what the other two leave behind, and drawing
 * it as a line says that without a legend.
 *
 * Recharts is stripped rather than used as it comes: no axis lines, no ticks,
 * a dashed hairline grid on the horizontal only, and every colour a token.
 */
export function MonthlyBars({
  months,
  onSelect,
}: {
  months: MonthPoint[]
  onSelect?: (month: string) => void
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart
        data={months}
        margin={{ top: 4, right: 4, bottom: 0, left: -12 }}
        onClick={(state) => {
          // ⚠️ Every chart is a starting point: a month you can see is a month
          // you can open. Recharts hands back the index, not the datum.
          const index = state?.activeTooltipIndex
          if (onSelect && typeof index === 'number' && months[index]) {
            onSelect(months[index].month)
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
        <YAxis tickFormatter={formatMoneyShort} width={64} {...axisProps} />
        <Tooltip cursor={CURSOR} content={<MoneyTooltip />} />

        <Bar dataKey="income_cents" name="Entrate" fill={MONEY.income} radius={[4, 4, 0, 0]} />
        <Bar dataKey="expense_cents" name="Uscite" fill={MONEY.expense} radius={[4, 4, 0, 0]} />
        <Line
          type="monotone"
          dataKey="savings_cents"
          name="Differenza"
          stroke={AXIS}
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
