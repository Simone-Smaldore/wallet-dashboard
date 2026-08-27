import { useMemo, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router'

import { useQuery } from '../../api/cache'
import {
  api,
  type Account,
  type Analysis,
  type CategorySlice,
  type MonthPoint,
} from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Dropdown } from '../../components/Dropdown'
import type { Group, Option } from '../../components/Dropdown'
import { EmptyState } from '../../components/EmptyState'
import { Field } from '../../components/Field'
import { IconButton } from '../../components/IconButton'
import { CategoryBars } from '../../components/charts/CategoryBars'
import { CategoryPie } from '../../components/charts/CategoryPie'
import { ChartFrame } from '../../components/charts/ChartFrame'
import { MonthlyBars } from '../../components/charts/MonthlyBars'
import { NetWorthArea } from '../../components/charts/NetWorthArea'
import { RangePicker } from '../../components/charts/RangePicker'
import { formatMoney, formatSigned } from '../../lib/money'
import { formatDayShort } from '../../lib/period'
import {
  alignedSpan,
  monthAbbr,
  monthName,
  monthOf,
  today,
  yearOf,
} from '../../lib/period'
import { TransactionRow } from '../transactions/TransactionRow'
import { TransactionSheet } from '../transactions/TransactionSheet'

/** Where the money went, and whether that is different from last time.
 *
 * ⚠️ Every number here can be opened. A chart is a starting point, not a
 * picture: from a slice you land on the movements that make it, because the
 * first instinct in front of "Trasporti 340 €" is "and where does that come
 * from?" — and a number you cannot open is a number you will not trust.
 */

type Grain = 'month' | 'quarter' | 'year' | 'custom'

const GRAIN_LABELS: Record<Grain, string> = {
  month: 'Mese',
  quarter: 'Trimestre',
  year: 'Anno',
  custom: 'Da–a',
}

/** How many whole months each grain spans, and how far an arrow moves.
 *
 * ⚠️ The spans are aligned to the calendar: the year is January to December and
 * the quarter is one of the four fixed ones, not the last twelve or three
 * months counted back from today. A rolling window means something different
 * every time it is opened, so two readings a week apart are not comparable —
 * and "the year" out loud has never meant "since last August". */
const SPAN: Record<'month' | 'quarter' | 'year', number> = {
  month: 1,
  quarter: 3,
  year: 12,
}

export function AnalisiPage() {
  const [grain, setGrain] = useState<Grain>('month')
  // The first day of the chosen block. Null until the calendar has loaded and
  // said which blocks exist.
  const [chosen, setChosen] = useState<string | null>(null)
  const [custom, setCustom] = useState(() => monthOf(today()))
  const [opening, setOpening] = useState<Analysis['top_expenses'][number] | null>(null)

  // ⚠️ Which periods can be looked at at all.
  //
  // Offering March 2019 and then explaining seven times over that there is
  // nothing in it is worse than not offering it: the screen looks broken, and
  // an honest message repeated seven times reads as an error rather than as an
  // answer. So the picker is built out of the months that actually have
  // movements, and the arrows step between them rather than into the void.
  const calendar = useQuery('/api/stats/calendar', api.calendar)
  const available = useMemo(() => {
    if (grain === 'custom') return []
    const size = SPAN[grain]
    const starts = new Set(
      (calendar.data?.months ?? []).map((month) => alignedSpan(month, size).start),
    )
    return [...starts].sort()
  }, [calendar.data, grain])

  // Keep the choice inside what exists: changing grain, or landing on a month
  // nothing has been recorded in yet, falls back to the most recent period
  // there is something to read.
  const start =
    grain === 'custom'
      ? null
      : chosen !== null && available.includes(chosen)
        ? chosen
        : (available.at(-1) ?? null)

  const period =
    grain === 'custom' ? custom : start === null ? null : alignedSpan(start, SPAN[grain])

  const key = period && `/api/stats/analysis?from=${period.start}&to=${period.end}`
  const { data, loading, error, refetch } = useQuery(
    key,
    () =>
      period
        ? api.analysis({ from: period.start, to: period.end })
        : Promise.reject(new Error('nessun periodo')),
    // ⚠️ The one read in the app that blocks the page, and only when it has
    // nothing to show. Everything here is a single answer to a single question
    // — seven charts over one period — so there is no half of it to draw while
    // the rest arrives, and it is the heaviest query the app makes. Better to
    // say "attendi" than to leave the screen blank and look broken. Coming back
    // to a period already loaded does not block: the data on screen is right.
    { blocking: true },
  )

  const at = start === null ? -1 : available.indexOf(start)
  const previous = at > 0 ? available[at - 1] : null
  const next = at >= 0 && at < available.length - 1 ? available[at + 1] : null

  return (
    <div className="flex flex-col gap-4">
      <h1 className="font-display text-title text-ink-1">Analisi</h1>

      <div className="flex flex-col gap-3">
        {/* A selector over one set of data — a period — which is what a
            segmented control is actually for. It is not hiding content. */}
        <div className="flex gap-2 self-start">
          {(Object.keys(GRAIN_LABELS) as Grain[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => {
                // Changing grain must keep you where you were looking: the
                // block widens or narrows around the period on screen instead
                // of jumping home. If the wider block has nothing in it, the
                // fallback above quietly moves to the nearest one that does.
                if (option === 'custom') setCustom(period ?? monthOf(today()))
                else if (period) setChosen(alignedSpan(period.start, SPAN[option]).start)
                setGrain(option)
              }}
              aria-pressed={grain === option}
              className={[
                'min-h-9 rounded-pill border px-3 text-caption transition-colors duration-200',
                grain === option
                  ? 'border-accent bg-accent-dim text-accent'
                  : 'border-border-soft text-ink-2 hover:bg-surface-hover',
              ].join(' ')}
            >
              {GRAIN_LABELS[option]}
            </button>
          ))}
        </div>

        {grain === 'custom' ? (
          /* ⚠️ The free range is the one place an empty period is allowed to be
             chosen: you typed those two dates, so being told there is nothing
             between them is an answer to a question you asked. */
          <div className="grid gap-3 sm:grid-cols-2">
            <Field
              label="Da"
              type="date"
              value={custom.start}
              onChange={(event) =>
                setCustom((range) => ({ ...range, start: event.target.value }))
              }
            />
            <Field
              label="A"
              type="date"
              value={custom.end}
              onChange={(event) =>
                setCustom((range) => ({ ...range, end: event.target.value }))
              }
            />
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <IconButton
              label="Periodo precedente"
              onClick={() => previous && setChosen(previous)}
              disabled={previous === null}
              Icon={ChevronLeft}
              size="md"
              iconSize={20}
            />

            {/* The arrows are for stepping; this is for getting to February
                2020 without pressing one of them seventy-two times. */}
            <div className="min-w-0 flex-1">
              <Dropdown
                placeholder="Scegli il periodo"
                value={start}
                onChange={(value) => value !== null && setChosen(value)}
                groups={periodGroups(available, SPAN[grain])}
              />
            </div>

            <IconButton
              label="Periodo successivo"
              onClick={() => next && setChosen(next)}
              disabled={next === null}
              Icon={ChevronRight}
              size="md"
              iconSize={20}
            />
          </div>
        )}
      </div>

      {period === null ? (
        <EmptyState title="Non c'è ancora niente da analizzare">
          Registra qualche movimento e questa schermata avrà di che parlare. I periodi che
          puoi scegliere qui sono quelli in cui hai registrato qualcosa.
        </EmptyState>
      ) : loading && !data ? null : error && !data ? (
        <EmptyState title="Non riesco a leggere l'analisi">
          {error.message}
          <Button variant="secondary" onClick={refetch} className="mt-4">
            Riprova
          </Button>
        </EmptyState>
      ) : data ? (
        <Charts analysis={data} onOpenMovement={setOpening} />
      ) : null}

      {opening ? (
        <TransactionSheet movement={opening} onClose={() => setOpening(null)} />
      ) : null}
    </div>
  )
}

/** The choosable periods, grouped by year when there is more than one a year.
 *
 * Labels are short on purpose — `gennaio`, `gen–mar`, `2026` — because the year
 * is already the group heading and repeating it in every row is noise. */
/** ⚠️ "Tutto" and "Solo liquido" first, then the accounts.
 *
 * The two summaries answer the question people actually ask — how much do I
 * have, and how much of it could I spend — and a single account is the follow
 * up. Putting the accounts first would bury both. */
function scopeGroups(accounts: Account[]): Group<Scope>[] {
  const open = accounts.filter((account) => !account.is_archived)

  return [
    {
      label: 'Tutto',
      options: [
        { value: 'all' as Scope, label: 'Patrimonio totale' },
        { value: 'liquid' as Scope, label: 'Solo liquido' },
      ],
    },
    {
      label: 'Un conto',
      options: open.map((account) => ({
        value: account.id as Scope,
        label: account.name,
      })),
    },
  ]
}

function periodGroups(starts: string[], size: number): Group<string>[] {
  if (size === 12) {
    return [
      {
        label: 'Anno',
        options: starts.map((start) => ({ value: start, label: String(yearOf(start)) })),
      },
    ]
  }

  const byYear = new Map<number, Option<string>[]>()
  for (const start of starts) {
    const label =
      size === 1
        ? monthName(start)
        : `${monthAbbr(start)}–${monthAbbr(alignedSpan(start, size).end)}`
    const year = yearOf(start)
    byYear.set(year, [...(byYear.get(year) ?? []), { value: start, label }])
  }

  // Newest year first: it is the one you almost always want.
  return [...byYear.entries()]
    .sort(([a], [b]) => b - a)
    .map(([year, options]) => ({ label: String(year), options }))
}

/** One long chart's own window.
 *
 * ⚠️ One of these per chart, not one for both. The two answer different
 * questions and want different spans: "am I spending more than I earn" is read
 * over months, "is my money growing" over years, and forcing them to agree
 * means one of the two is always shown at the wrong length. They cost one small
 * request each, cached per window, so the second visit to a span is instant.
 */
function useSeries(end: string, initial: number, scope: Scope = 'all') {
  const [range, setRange] = useState(initial)

  const where =
    scope === 'all' ? {} : scope === 'liquid' ? { liquid: true } : { account_id: scope }
  const key = `/api/stats/series?months=${range}&end=${end}&scope=${scope}`

  const { data } = useQuery(key, () => api.series({ months: range, end, ...where }))

  // ⚠️ Keep the last window drawn while a wider one loads. Blanking a chart to
  // redraw the same shape one year longer reads as a fault; leaving it up and
  // letting it grow reads as what it is.
  const drawn = useRef<MonthPoint[]>([])
  if (data) drawn.current = data.months

  return {
    months: data?.months ?? drawn.current,
    pricedFrom: data?.priced_from ?? null,
    range,
    setRange,
  }
}

/** What the net-worth curve is drawing: everything, only what is spendable, or
 *  one account on its own. */
type Scope = 'all' | 'liquid' | number

function Charts({
  analysis,
  onOpenMovement,
}: {
  analysis: Analysis
  onOpenMovement: (movement: Analysis['top_expenses'][number]) => void
}) {
  const navigate = useNavigate()

  // The trailing windows end where the chosen period ends, so stepping back a
  // month walks both trends back with it.
  const [scope, setScope] = useState<Scope>('all')
  const accounts = useQuery('/api/accounts', api.accounts)

  const flows = useSeries(analysis.period.end, 12)
  const worth = useSeries(analysis.period.end, 12, scope)
  const { period, totals, previous_totals: before, pace } = analysis
  const nothing = totals.movement_count === 0

  /** Land on the list, filtered exactly the way this number was computed. */
  function openMovements(extra: Record<string, string | number> = {}) {
    const params = new URLSearchParams({ from: period.start, to: period.end })
    for (const [name, value] of Object.entries(extra)) params.set(name, String(value))
    void navigate(`/movimenti?${params.toString()}`)
  }

  function openSlice(slice: CategorySlice) {
    if (slice.category_id === null) {
      // "Senza categoria" has no id to filter by; the kind gets you close.
      openMovements({ kind: 'expense' })
      return
    }
    openMovements({ category_id: slice.category_id })
  }

  return (
    <div className="flex flex-col gap-3">
      <Card>
        <p className="text-micro uppercase text-ink-3">Nel periodo</p>
        {nothing ? (
          <p className="mt-3 text-body text-ink-2">
            Nessun movimento registrato in questo periodo. Non è uno zero: è che non c'è
            niente da leggere.
          </p>
        ) : (
          <div className="mt-3 grid grid-cols-3 gap-3">
            <Figure
              label="Entrate"
              value={formatMoney(totals.income_cents)}
              tone="text-money-income"
              change={totals.income_cents - before.income_cents}
              onClick={() => openMovements({ kind: 'income' })}
            />
            <Figure
              label="Uscite"
              value={formatMoney(totals.expense_cents)}
              tone="text-money-expense"
              change={totals.expense_cents - before.expense_cents}
              onClick={() => openMovements({ kind: 'expense' })}
            />
            <Figure
              label="Risparmio"
              value={formatSigned(totals.savings_cents)}
              tone={totals.savings_cents < 0 ? 'text-money-expense' : 'text-ink-1'}
              change={totals.savings_cents - before.savings_cents}
            />
          </div>
        )}
      </Card>

      <ChartFrame
        title="Uscite per categoria"
        empty={totals.expense_cents === 0}
        emptyText="Nessuna uscita in questo periodo."
      >
        {/* The ring is the shape, the list is the numbers — and the list is
            also the ring's legend, which is why they share one frame instead of
            being two cards saying the same thing twice. */}
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:gap-6">
          <div className="sm:w-[240px] sm:shrink-0">
            <CategoryPie
              slices={analysis.by_category}
              total={totals.expense_cents}
              onOpen={openSlice}
            />
          </div>
          <div className="min-w-0 flex-1">
            <CategoryBars slices={analysis.by_category} onOpen={openSlice} />
          </div>
        </div>
      </ChartFrame>

      <ChartFrame
        title="Entrate e uscite, mese per mese"
        aside={<RangePicker value={flows.range} onChange={flows.setRange} />}
        empty={
          flows.months.length === 0 ||
          flows.months.every((month) => month.movement_count === 0)
        }
        emptyText="Nessun movimento in questa finestra."
      >
        <MonthlyBars
          months={flows.months}
          onSelect={(month) => {
            const span = monthOf(month)
            void navigate(`/movimenti?from=${span.start}&to=${span.end}`)
          }}
        />
      </ChartFrame>

      <ChartFrame
        title="Patrimonio a fine mese"
        aside={<RangePicker value={worth.range} onChange={worth.setRange} />}
        empty={worth.months.length === 0}
      >
        <div className="mb-3 max-w-[260px]">
          <Dropdown
            placeholder="Cosa mostrare"
            value={typeof scope === 'number' ? scope : scope}
            onChange={(value) => setScope((value ?? 'all') as Scope)}
            groups={scopeGroups(accounts.data?.accounts ?? [])}
          />
        </div>

        <NetWorthArea months={worth.months} />

        {/* ⚠️ Where the prices begin, said out loud. Before that day the curve
            draws the capital paid in, which is a different quantity — so the
            first priced month steps up by everything the holdings had gained in
            silence, and without this line that step reads as a very good
            month. */}
        {worth.pricedFrom && worth.months.length > 0 &&
        worth.months[0].month < worth.pricedFrom &&
        scope !== 'liquid' ? (
          <p className="mt-3 text-caption text-ink-3">
            Prima del {formatDayShort(worth.pricedFrom)} non avevo i prezzi: lì la curva
            mostra quanto avevi versato, non quanto valeva. Il gradino è il guadagno
            accumulato fino a quel giorno, non quello di un mese.
          </p>
        ) : null}
      </ChartFrame>

      <ChartFrame
        title="Le uscite più grandi"
        empty={analysis.top_expenses.length === 0}
        emptyText="Nessuna uscita in questo periodo."
      >
        {/* Pulled out to the card's edge so the rows keep their own padding
            and still line up with the title above them. */}
        <ul className="-mx-4 divide-y divide-border-soft sm:-mx-5">
          {analysis.top_expenses.map((movement) => (
            <TransactionRow
              key={movement.id}
              movement={movement}
              onOpen={() => onOpenMovement(movement)}
            />
          ))}
        </ul>
      </ChartFrame>

      <ChartFrame
        title="Ritmo di spesa"
        empty={pace.elapsed_days === 0}
        emptyText="Il periodo non è ancora cominciato."
      >
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-caption text-ink-2">Media al giorno</dt>
            <dd className="num mt-0.5 text-title text-ink-1">
              {formatMoney(pace.daily_average_cents)}
            </dd>
            <dd className="mt-1 text-caption text-ink-3">
              su {pace.elapsed_days} giorni di {pace.total_days}
            </dd>
          </div>
          <div>
            <dt className="text-caption text-ink-2">A fine periodo</dt>
            <dd className="num mt-0.5 text-title text-ink-1">
              {formatMoney(pace.projection_cents)}
            </dd>
            {/* ⚠️ Called what it is. It is this rate carried forward, it knows
                nothing about the rent due on the 28th, and dressing it up as a
                forecast would be the app starting to give advice. */}
            <dd className="mt-1 text-caption text-ink-3">proiezione lineare</dd>
          </div>
        </dl>
      </ChartFrame>
    </div>
  )
}

function Figure({
  label,
  value,
  tone,
  change,
  onClick,
}: {
  label: string
  value: string
  tone: string
  change: number
  onClick?: () => void
}) {
  const body = (
    <>
      <p className="truncate text-caption text-ink-2">{label}</p>
      <p className={`num mt-0.5 truncate text-heading ${tone}`}>{value}</p>
      {/* Neutral ink on purpose: the change is a fact, not a verdict. */}
      <p className="num mt-0.5 truncate text-caption text-ink-3">{formatSigned(change)}</p>
    </>
  )

  return onClick ? (
    <button
      type="button"
      onClick={onClick}
      className="-mx-2 min-w-0 rounded-control px-2 py-1 text-left transition-colors duration-200 hover:bg-surface-hover"
    >
      {body}
    </button>
  ) : (
    <div className="min-w-0 px-2 py-1">{body}</div>
  )
}
