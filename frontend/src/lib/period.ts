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

export function shiftDays(iso: string, days: number): string {
  const [year, month, day] = parts(iso)
  const moved = new Date(year, month - 1, day + days)
  return toIso(moved.getFullYear(), moved.getMonth() + 1, moved.getDate())
}

export function isFuture(iso: string): boolean {
  return iso > today()
}
