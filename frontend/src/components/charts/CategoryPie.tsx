import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import type { CategorySlice } from '../../api/client'
import { AXIS, CURSOR, seriesColor } from '../../lib/chart'
import { formatMoney, formatShare } from '../../lib/money'

/** How the spending of a period divides up.
 *
 * A ring rather than a full pie: the hole is where the total goes, and the
 * total is the number the shape is a proportion *of*. A pie with the sum
 * written outside it makes you look in two places.
 *
 * ⚠️ **Six slices, then "Altro".** More than six wedges stop being tellable
 * apart, and the answer is to group the tail rather than to invent more tints —
 * the rule DESIGN.md states for charts. The list underneath still shows every
 * category, so nothing is hidden: what is grouped here is the *drawing*, not
 * the data.
 *
 * ⚠️ Each wedge takes **its own category's colour**, the one that category
 * carries in its icon and in the list below. That is a deliberate reading of
 * "charts use the first six series only": the point of that rule is not to run
 * out of distinguishable colours, and using a seventh palette entry that the
 * category already owns everywhere else is more legible, not less. Two
 * categories can share a colour, which is why the list below is the legend.
 */

const MAX_SLICES = 6
const OTHER = 'Altro'

type Wedge = {
  key: string
  name: string
  value: number
  color: string
  categoryId: number | null | 'other'
}

export function CategoryPie({
  slices,
  total,
  onOpen,
}: {
  slices: CategorySlice[]
  total: number
  onOpen: (slice: CategorySlice) => void
}) {
  const drawn = slices.filter((slice) => slice.total_cents > 0)
  const head = drawn.slice(0, MAX_SLICES)
  const tail = drawn.slice(MAX_SLICES)

  const wedges: Wedge[] = head.map((slice) => ({
    key: String(slice.category_id ?? 'none'),
    name: slice.name,
    value: slice.total_cents,
    color: seriesColor(slice.color),
    categoryId: slice.category_id,
  }))

  if (tail.length > 0) {
    wedges.push({
      key: 'other',
      name: OTHER,
      // Integers, so this sum is exact and the wedges add up to the total.
      value: tail.reduce((sum, slice) => sum + slice.total_cents, 0),
      color: AXIS,
      categoryId: 'other',
    })
  }

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={wedges}
            dataKey="value"
            nameKey="name"
            innerRadius="62%"
            outerRadius="100%"
            paddingAngle={2}
            stroke="none"
            isAnimationActive={false}
            onClick={(_, index) => {
              const wedge = wedges[index]
              const slice = drawn.find((row) => row.category_id === wedge?.categoryId)
              // "Altro" is several categories at once; it has nothing single to
              // open, so it stays put rather than opening something arbitrary.
              if (slice) onOpen(slice)
            }}
          >
            {wedges.map((wedge) => (
              <Cell key={wedge.key} fill={wedge.color} className="cursor-pointer" />
            ))}
          </Pie>
          <Tooltip cursor={CURSOR} content={<SliceTooltip total={total} />} />
        </PieChart>
      </ResponsiveContainer>

      {/* In the hole, and not clickable: it is a label, not a control. */}
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="text-center">
          <p className="text-micro uppercase text-ink-3">Uscite</p>
          <p className="num text-heading text-ink-1">{formatMoney(total)}</p>
        </div>
      </div>
    </div>
  )
}

function SliceTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean
  payload?: Array<{ name?: string; value?: number | string; payload?: Wedge }>
  total: number
}) {
  const entry = payload?.[0]
  if (!active || !entry) return null

  const value = Number(entry.value ?? 0)
  // ⚠️ Worked out here rather than read off the server's `share_permille`: this
  // wedge can be "Altro", which is several categories added together and has no
  // share of its own. Integers all the way, rounded once.
  const permille = total > 0 ? Math.round((value * 1000) / total) : 0

  return (
    <div className="rounded-control border border-border-strong bg-bg-raise px-3 py-2 shadow-card">
      <p className="text-caption text-ink-2">{entry.payload?.name ?? entry.name}</p>
      <p className="num text-caption text-ink-1">
        {formatMoney(value)} <span className="text-ink-3">· {formatShare(permille)}</span>
      </p>
    </div>
  )
}
