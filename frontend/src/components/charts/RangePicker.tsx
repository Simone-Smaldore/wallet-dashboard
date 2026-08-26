/** How far back one long chart looks: 6M · 1A · 3A · 5A · Max.

 * ⚠️ **One per chart, not one for both.** The two long charts answer different
 * questions and want different spans: "am I spending more than I earn" is read
 * over months, "is my money growing" over years. Forcing them to agree means
 * one of the two is always shown at the wrong length.
 *
 *
 * ⚠️ **This is not the period selector**, and the difference is the whole point
 * of having two. The one at the top of the screen picks *what to break down* —
 * which month's spending, which quarter's categories. This picks *how far back
 * the trend goes*, and a trend is not a period: "how am I doing" is a question
 * about the last few years, asked while looking at March.
 *
 * They are also fetched separately, so widening a line does not re-fetch a pie.
 *
 * `0` is Max, and it means "since the first movement" rather than some large
 * number of months: fifty years of zeros in front of a life that started four
 * months ago is a chart that lies about its own subject.
 */

export const RANGES = [
  { months: 6, label: '6M' },
  { months: 12, label: '1A' },
  { months: 36, label: '3A' },
  { months: 60, label: '5A' },
  { months: 0, label: 'Max' },
] as const

export function RangePicker({
  value,
  onChange,
}: {
  value: number
  onChange: (months: number) => void
}) {
  return (
    <div className="flex gap-1" role="group" aria-label="Quanto indietro">
      {RANGES.map((range) => (
        <button
          key={range.months}
          type="button"
          onClick={() => onChange(range.months)}
          aria-pressed={value === range.months}
          className={[
            'min-h-7 rounded-pill px-2 text-micro transition-colors duration-200',
            value === range.months
              ? 'bg-accent-dim text-accent'
              : 'text-ink-3 hover:bg-surface-hover hover:text-ink-1',
          ].join(' ')}
        >
          {range.label}
        </button>
      ))}
    </div>
  )
}
