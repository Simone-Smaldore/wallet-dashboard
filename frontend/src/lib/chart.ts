/** Chart colours and defaults.
 *
 * ⚠️ **The only file in the frontend that names a colour for a chart.** Recharts
 * ships a palette of its own and every component that draws would otherwise
 * carry a hex or two; both are things DESIGN.md forbids. Everything here is a
 * `var(--color-…)` reference, so retuning a series in tokens.css retunes every
 * chart and nothing has to be found and edited.
 *
 * ⚠️ Six series and no more. Past six, lines stop being tellable apart on a
 * phone; a chart with more slices than that groups the tail rather than
 * inventing tints. The four extra category colours exist for lists, not charts.
 */

/** The series, in order. */
export const CHART_SERIES = [
  'var(--color-chart-1)',
  'var(--color-chart-2)',
  'var(--color-chart-3)',
  'var(--color-chart-4)',
  'var(--color-chart-5)',
  'var(--color-chart-6)',
] as const

/** The four money colours, which are semantics rather than decoration:
 *  income green, spending red, transfers cyan and unsigned, adjustments ochre. */
export const MONEY = {
  income: 'var(--color-money-income)',
  expense: 'var(--color-money-expense)',
  transfer: 'var(--color-money-transfer)',
  adjustment: 'var(--color-money-adjustment)',
} as const

export const GRID = 'var(--color-chart-grid)'
export const AXIS = 'var(--color-chart-axis)'
export const INK_2 = 'var(--color-ink-2)'

/** A category's own colour, or a neutral one when it has none.
 *
 * The uncategorised bucket is real — the category is optional at the till on
 * purpose — and it gets the muted ink rather than a series colour, so it reads
 * as "no answer" instead of as one more category. */
export function seriesColor(token: string | null | undefined): string {
  if (!token) return AXIS
  return `var(--color-${token})`
}

/** What every axis in this app looks like: no line, no ticks, small muted
 *  labels. Recharts draws a full axis by default and it does not belong. */
export const axisProps = {
  stroke: AXIS,
  tickLine: false,
  axisLine: false,
  tick: { fill: AXIS, fontSize: 11 },
} as const

/** The band behind the hovered column. The box itself is a component —
 *  see components/charts/MoneyTooltip.tsx — rather than a pile of inline
 *  styles bolted onto the library's default. */
export const CURSOR = { fill: 'var(--color-surface-hover)' } as const
