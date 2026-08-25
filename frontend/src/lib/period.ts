/** Periods. Mirror of backend/app/domain/period.py.
 *
 * ⚠️ The only place in the frontend where date arithmetic happens. It is the
 * kind of code that diverges quietly, and when it diverges a movement dated the
 * 31st lands in two months or in none.
 *
 * Dates travel as `YYYY-MM-DD` strings, which is what the API speaks and what
 * `<input type="date">` reads and writes. No Date objects cross this boundary:
 * `new Date('2026-03-01')` is parsed as UTC midnight and, west of Greenwich,
 * prints as the 28th of February.
 */

const MONTHS = [
  'gennaio',
  'febbraio',
  'marzo',
  'aprile',
  'maggio',
  'giugno',
  'luglio',
  'agosto',
  'settembre',
  'ottobre',
  'novembre',
  'dicembre',
]

const WEEKDAYS = [
  'domenica',
  'lunedì',
  'martedì',
  'mercoledì',
  'giovedì',
  'venerdì',
  'sabato',
]

export type Period = { start: string; end: string }

/** Today, as the calendar on the wall sees it — not as UTC does. */
export function today(): string {
  const now = new Date()
  return toIso(now.getFullYear(), now.getMonth() + 1, now.getDate())
}

function toIso(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function parts(iso: string): [number, number, number] {
  const [year, month, day] = iso.split('-').map(Number)
  return [year, month, day]
}

function lastDayOf(year: number, month: number): number {
  // Day 0 of the next month is the last day of this one.
  return new Date(year, month, 0).getDate()
}

/** The calendar month a date falls in. Both ends belong to it. */
export function monthOf(iso: string): Period {
  const [year, month] = parts(iso)
  return { start: toIso(year, month, 1), end: toIso(year, month, lastDayOf(year, month)) }
}

/** Move by whole months, clamping the day to what the target month has.
 *
 * ⚠️ 31 January plus one month is 28 or 29 February — there is no 31st.
 * Clamping is the only answer that does not roll silently into March. */
export function shiftMonth(iso: string, months: number): string {
  const [year, month, day] = parts(iso)
  const index = month - 1 + months
  const targetYear = year + Math.floor(index / 12)
  const targetMonth = ((index % 12) + 12) % 12 + 1
  return toIso(targetYear, targetMonth, Math.min(day, lastDayOf(targetYear, targetMonth)))
}

/** `marzo 2026`. Italian, and not from the browser locale: product text is not
 *  something to leave to whatever language the phone is set to. */
export function formatMonth(iso: string): string {
  const [year, month] = parts(iso)
  return `${MONTHS[month - 1]} ${year}`
}

/** `giovedì 12 marzo` — the heading of a day in the movements list.
 *
 * Today and yesterday are named instead: on the screen you look at most often,
 * "oggi" is what you are actually looking for. */
export function formatDay(iso: string): string {
  const now = today()
  if (iso === now) return 'Oggi'
  if (iso === shiftDays(now, -1)) return 'Ieri'

  const [year, month, day] = parts(iso)
  const weekday = WEEKDAYS[new Date(year, month - 1, day).getDay()]
  const sameYear = year === parts(now)[0]
  return sameYear
    ? `${weekday} ${day} ${MONTHS[month - 1]}`
    : `${weekday} ${day} ${MONTHS[month - 1]} ${year}`
}

/** The calendar block of `size` whole months that `iso` falls in.
 *
 * `size` is 1, 3 or 12 — a month, a quarter, a year — and the block is aligned
 * to the calendar, not to today: asking for the year in August 2026 gives
 * January to December 2026, and the quarter gives July to September.
 *
 * ⚠️ Aligned rather than rolling, and this is the whole point. "The last twelve
 * months" is a window that means something different every time you open it, so
 * two readings a week apart are not comparable and neither matches anything you
 * would call a year out loud. A calendar year also lines up with the things
 * that are actually annual — the insurance, the tax, the holidays — which is
 * what makes one year worth putting next to another.
 *
 * Whole months rather than "ninety days" for the same reason: a quarter that
 * started on the 14th would compare against a quarter starting on the 14th of
 * another month, and no bill in anybody's life works that way.
 */
export function alignedSpan(iso: string, size: number): Period {
  const [year, month] = parts(iso)
  // 12 must be divisible by size, or the blocks would not tile the year.
  const first = Math.floor((month - 1) / size) * size + 1
  const start = toIso(year, first, 1)
  return { start, end: monthOf(shiftMonth(start, size - 1)).end }
}

/** The label of a whole period: `marzo 2026`, `2026`, or `9 – 15 marzo 2026`.
 *
 * A month and a year say their name; anything else says its two ends, dropping
 * what the two have in common so a week inside one month does not repeat the
 * month twice.
 */
export function formatRange(period: Period): string {
  const [fromYear, fromMonth, fromDay] = parts(period.start)
  const [toYear, toMonth, toDay] = parts(period.end)

  const month = monthOf(period.start)
  if (month.start === period.start && month.end === period.end) {
    return formatMonth(period.start)
  }
  if (fromMonth === 1 && fromDay === 1 && toMonth === 12 && toDay === 31 && fromYear === toYear) {
    return String(fromYear)
  }

  if (fromYear === toYear && fromMonth === toMonth) {
    return `${fromDay} – ${toDay} ${MONTHS[toMonth - 1]} ${toYear}`
  }
  if (fromYear === toYear) {
    return `${fromDay} ${MONTHS[fromMonth - 1]} – ${toDay} ${MONTHS[toMonth - 1]} ${toYear}`
  }
  return `${fromDay} ${MONTHS[fromMonth - 1]} ${fromYear} – ${toDay} ${MONTHS[toMonth - 1]} ${toYear}`
}

/** `27 nov` — a day named in a sentence, where the weekday is noise.
 *
 * Used by the savings card, which says "from the salary of 27 nov to 26 dec":
 * there the two dates are the ends of a stretch, not appointments. */
export function formatDayShort(iso: string): string {
  const [year, month, day] = parts(iso)
  const sameYear = year === parts(today())[0]
  const label = `${day} ${MONTHS[month - 1].slice(0, 3)}`
  return sameYear ? label : `${label} ${year}`
}

/** `gennaio` — the month's name on its own, for a picker. */
export function monthName(iso: string): string {
  return MONTHS[parts(iso)[1] - 1]
}

/** `gen` — three letters, always, with no year attached.
 *
 * Distinct from `monthTick`, which puts the year on January because on a
 * twelve-month axis that is the one tick where the reader needs to know the
 * line has crossed into another year. In a list grouped by year that would be
 * saying it twice. */
export function monthAbbr(iso: string): string {
  return MONTHS[parts(iso)[1] - 1].slice(0, 3)
}

export function yearOf(iso: string): number {
  return parts(iso)[0]
}

/** `mar` — a month on a chart axis, where twelve full names would not fit.
 *
 * January carries its year: it is the only tick where the reader needs to know
 * the line has crossed into another one. */
export function monthTick(iso: string): string {
  const [year, month] = parts(iso)
  const short = MONTHS[month - 1].slice(0, 3)
  return month === 1 ? `${short} ${String(year).slice(2)}` : short
}

export function shiftDays(iso: string, days: number): string {
  const [year, month, day] = parts(iso)
  const moved = new Date(year, month - 1, day + days)
  return toIso(moved.getFullYear(), moved.getMonth() + 1, moved.getDate())
}

export function isFuture(iso: string): boolean {
  return iso > today()
}
