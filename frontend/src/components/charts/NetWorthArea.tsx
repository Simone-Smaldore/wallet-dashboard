import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { MonthPoint } from '../../api/client'
import { CURSOR, GRID, axisProps, tickInterval } from '../../lib/chart'
import { formatMoneyShort } from '../../lib/money'
import { monthTick } from '../../lib/period'
import { MoneyTooltip } from './MoneyTooltip'

/** The long curve: what everything was worth at the end of each month.
 *
 * ⚠️ The axis does not start at zero, and that is deliberate here: this chart
 * answers "is it going up", and a scale from zero would flatten a year of
 * saving into a straight line. It is the one chart in the app where the shape
 * matters more than the magnitude — every other number is shown whole, in
 * euro, exactly where it can be checked.
 *
 * This is also the chart V2 will pour investments into. The shape does not
 * change, only what is summed into each point.
 */
export function NetWorthArea({ months }: { months: MonthPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={months} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
        <defs>
          {/* A fade rather than a flat fill: the area is there to give the line
              a body, not to be read as a quantity of its own. */}
          <linearGradient id="net-worth-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.28} />
            <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis
          dataKey="month"
          tickFormatter={monthTick}
          interval={tickInterval(months.length)}
          {...axisProps}
        />
        <YAxis
          tickFormatter={formatMoneyShort}
          width={64}
          domain={['auto', 'auto']}
          {...axisProps}
        />
        <Tooltip cursor={CURSOR} content={<MoneyTooltip />} />

        <Area
          type="monotone"
          dataKey="net_worth_cents"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          fill="url(#net-worth-fill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
