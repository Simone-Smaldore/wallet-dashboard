import { useState } from 'react'
import { ChevronRight, Pencil } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useQuery } from '../../api/cache'
import { api, type Account, type Summary } from '../../api/client'
import { Amount } from '../../components/Amount'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { EmptyState } from '../../components/EmptyState'
import { IconButton } from '../../components/IconButton'
import { formatMoney, formatSigned } from '../../lib/money'
import { formatDayShort, formatMonth } from '../../lib/period'
import { TransactionRow } from '../transactions/TransactionRow'
import { TransactionSheet } from '../transactions/TransactionSheet'
import { SavingsTargetSheet } from './SavingsTargetSheet'

/** The opening screen, and the one question you ask every day: how much is
 *  there, and what has been happening this month.
 *
 * One request draws all of it. Splitting it per card would be tidier and would
 * cost three round trips on a serverless function that starts cold — on the
 * screen that gets opened more often than any other.
 */
export function RiepilogoPage() {
  const { data, error, refetch } = useQuery('/api/stats/summary', () => api.summary())
  const [editingTarget, setEditingTarget] = useState(false)
  const [opening, setOpening] = useState<Summary['recent'][number] | null>(null)

  if (error && !data) {
    return (
      <EmptyState title="Non riesco a leggere il riepilogo">
        {error.message}
        <Button variant="secondary" onClick={refetch} className="mt-4">
          Riprova
        </Button>
      </EmptyState>
    )
  }
  // ⚠️ Nothing is remembered on this screen — it is all amounts, and amounts
  // do not come off a disk. So while the first request is in flight the page
  // draws itself with its numbers held at a dash, instead of a blank rectangle
  // under a scrim. A screen that is filling in is not a screen that is broken,
  // and it should not look like one.
  if (!data) return <Skeleton />

  const nothingYet = data.accounts.length === 0

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-title text-ink-1">Riepilogo</h1>

      <Card>
        <p className="text-micro uppercase text-ink-3">Patrimonio</p>
        <p className="num mt-1 text-hero text-ink-1">{formatMoney(data.net_worth_cents)}</p>
        <p className="mt-1 text-caption text-ink-2">{formatMonth(data.period.start)}</p>
      </Card>

      {nothingYet ? (
        <EmptyState title="Non c'è ancora niente da riassumere">
          Comincia dai conti: dove tieni i soldi e quanto c'è sopra oggi. Da lì in poi
          questa schermata si riempie da sola.
          <Link to="/conti" className="mt-4 inline-block">
            <Button variant="secondary">Vai ai conti</Button>
          </Link>
        </EmptyState>
      ) : (
        <>
          <MonthTotals summary={data} />
          <SavingsTarget summary={data} onEdit={() => setEditingTarget(true)} />
          <Accounts accounts={data.accounts} />
          <Recent summary={data} onOpen={setOpening} />
        </>
      )}

      {editingTarget ? (
        <SavingsTargetSheet
          savings={data.savings}
          onClose={() => setEditingTarget(false)}
        />
      ) : null}

      {opening ? (
        <TransactionSheet movement={opening} onClose={() => setOpening(null)} />
      ) : null}
    </div>
  )
}

/** The shape of the page, before the numbers arrive. */
function Skeleton() {
  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-title text-ink-1">Riepilogo</h1>
      <Card>
        <p className="text-micro uppercase text-ink-3">Patrimonio</p>
        <p className="mt-1 text-hero text-ink-1">
          <Amount cents={0} pending />
        </p>
      </Card>
      <Card>
        <p className="text-micro uppercase text-ink-3">Questo mese</p>
        <div className="mt-3 grid grid-cols-3 gap-3">
          {['Entrate', 'Uscite', 'Risparmio'].map((label) => (
            <div key={label} className="min-w-0">
              <p className="truncate text-caption text-ink-2">{label}</p>
              <p className="mt-0.5 text-heading text-ink-1">
                <Amount cents={0} pending />
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

/** ⚠️ Three numbers, and transfers are in none of them. The rule arrives
 *  applied from domain/stats.py; nothing here re-decides what counts. */
function MonthTotals({ summary }: { summary: Summary }) {
  const { income_cents, expense_cents, savings_cents, movement_count } = summary.totals

  return (
    <Card>
      <p className="text-micro uppercase text-ink-3">Questo mese</p>

      {movement_count === 0 ? (
        <p className="mt-3 text-body text-ink-2">
          Nessun movimento registrato in {formatMonth(summary.period.start)}.
        </p>
      ) : (
        <dl className="mt-3 grid grid-cols-3 gap-3">
          <Figure label="Entrate" value={formatMoney(income_cents)} tone="text-money-income" />
          <Figure label="Uscite" value={formatMoney(expense_cents)} tone="text-money-expense" />
          <Figure
            label="Risparmio"
            value={formatSigned(savings_cents)}
            tone={savings_cents < 0 ? 'text-money-expense' : 'text-ink-1'}
          />
        </dl>
      )}
    </Card>
  )
}

function Figure({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="min-w-0">
      <dt className="truncate text-caption text-ink-2">{label}</dt>
      <dd className={`num mt-0.5 truncate text-heading ${tone}`}>{value}</dd>
    </div>
  )
}

/** The savings goal, judged the way a salary judges it.
 *
 * ⚠️ **The unit is the salary cycle, not the calendar month.** Money lands on
 * the 27th, and the question worth answering is whether November's salary was
 * still partly there when December's arrived — a month boundary cuts that
 * stretch in half and answers something nobody asked. So the verdict belongs to
 * the cycle a new salary has already **closed**: it is the only stretch whose
 * spending is finished.
 *
 * The cycle being lived gets an allowance instead of a verdict — what can still
 * be spent and still land on the target. A verdict on a fortnight that is half
 * over would be a guess wearing the clothes of a result.
 *
 * ⚠️ Every state that is missing something says which thing, in words. No
 * target, no salary category, only one salary so far: three different reasons
 * there is nothing to show, and three different sentences. A bar at zero would
 * be the same picture for all of them and true for none.
 */
function SavingsTarget({ summary, onEdit }: { summary: Summary; onEdit: () => void }) {
  const { target_cents: target, closed, open, met, allowance_cents: allowance } =
    summary.savings

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-micro uppercase text-ink-3">Obiettivo di risparmio</p>
          <Verdict summary={summary} />
        </div>

        <div className="-mr-1.5 -mt-1.5 shrink-0">
          <IconButton
            label={target === null ? 'Imposta un obiettivo' : "Modifica l'obiettivo"}
            onClick={onEdit}
            Icon={Pencil}
          />
        </div>
      </div>

      {target !== null && open !== null && allowance !== null ? (
        <Allowance cycle={open} target={target} allowance={allowance} />
      ) : null}

      {closed !== null && target !== null ? (
        <p className="mt-3 border-t border-border-soft pt-3 text-caption text-ink-2">
          {met ? '✓ ' : ''}
          Dallo stipendio del {formatDayShort(closed.start)} al{' '}
          {formatDayShort(closed.end)} hai messo da parte{' '}
          <span className="num text-ink-1">{formatMoney(closed.saved_cents)}</span> di{' '}
          <span className="num">{formatMoney(target)}</span>.
        </p>
      ) : null}
    </Card>
  )
}

/** What the last completed cycle decided. */
function Verdict({ summary }: { summary: Summary }) {
  const { target_cents: target, salary_category_id: salaryId, closed, met } =
    summary.savings

  if (target === null) {
    return (
      <p className="mt-2 text-body text-ink-2">
        Non ne hai impostato uno. Se ti dai una cifra, qui vedrai quanto puoi ancora
        spendere prima del prossimo stipendio.
      </p>
    )
  }

  if (salaryId === null) {
    return (
      <p className="mt-2 text-body text-ink-2">
        Dimmi quale categoria è lo stipendio: il conto va da uno stipendio al successivo,
        non da un primo del mese all'altro.
      </p>
    )
  }

  if (closed === null) {
    return (
      <p className="mt-2 text-body text-ink-2">
        Aspetto il prossimo stipendio: è quello che dice come è andato questo.
      </p>
    )
  }

  return (
    <p className={`mt-1 text-title ${met ? 'text-money-income' : 'text-money-expense'}`}>
      {met ? 'Obiettivo raggiunto' : 'Obiettivo mancato'}
    </p>
  )
}

/** What is left to spend before the next salary.
 *
 * ⚠️ The one number on this screen you can still act on. The bar fills with
 * what has been spent against what was spendable — salary minus target — so
 * "full" means "you are at the line", not "well done".
 */
function Allowance({
  cycle,
  target,
  allowance,
}: {
  cycle: Summary['savings']['open'] & object
  target: number
  allowance: number
}) {
  const spendable = cycle.salary_cents - target
  const used = spendable > 0 ? Math.min(100, (cycle.spent_cents / spendable) * 100) : 100
  const over = allowance < 0

  return (
    <div className="mt-3">
      <p className="num text-hero text-ink-1">{formatMoney(Math.abs(allowance))}</p>
      <p className="mt-1 text-caption text-ink-2">
        {over
          ? 'oltre l’obiettivo, da quando è arrivato lo stipendio'
          : 'puoi ancora spenderli prima del prossimo stipendio'}
      </p>

      <div className="mt-3 h-2 overflow-hidden rounded-pill bg-surface-card-2">
        <div
          className={`h-full rounded-pill ${over ? 'bg-money-expense' : 'bg-accent'}`}
          style={{ width: `${used}%` }}
        />
      </div>
      <p className="mt-2 text-caption text-ink-3">
        <span className="num">{formatMoney(cycle.spent_cents)}</span> spesi su{' '}
        <span className="num">{formatMoney(Math.max(spendable, 0))}</span> dal{' '}
        {formatDayShort(cycle.start)}
      </p>
    </div>
  )
}

/** The balances, again — the same numbers the Conti screen shows, from the same
 *  formula. Archived accounts appear only while they still hold money: hiding a
 *  balance that is counted in the total would make the total look wrong. */
function Accounts({ accounts }: { accounts: Account[] }) {
  const shown = accounts.filter(
    (account) => !account.is_archived || account.balance_cents !== 0,
  )

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3 px-1">
        <h2 className="text-micro uppercase text-ink-3">Conti</h2>
        <Link
          to="/conti"
          className="flex items-center gap-1 text-caption text-ink-2 transition-colors duration-200 hover:text-ink-1"
        >
          Gestisci
          <ChevronRight size={14} strokeWidth={2} aria-hidden />
        </Link>
      </div>

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((account) => (
          <li key={account.id}>
            {/* Opening an account means seeing what happened on it, so the card
                leads to its movements rather than to its settings. */}
            <Link
              to={`/movimenti?account_id=${account.id}`}
              className="flex flex-col gap-1 rounded-card border border-border-soft bg-surface-card p-4 shadow-card transition-colors duration-200 hover:bg-surface-hover"
            >
              <p className="truncate text-caption text-ink-2">{account.name}</p>
              <p
                className={`num text-heading ${
                  account.balance_cents < 0 ? 'text-money-expense' : 'text-ink-1'
                }`}
              >
                {formatMoney(account.balance_cents)}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Recent({
  summary,
  onOpen,
}: {
  summary: Summary
  onOpen: (movement: Summary['recent'][number]) => void
}) {
  const navigate = useNavigate()

  if (summary.recent.length === 0) return null

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3 px-1">
        <h2 className="text-micro uppercase text-ink-3">Ultimi movimenti</h2>
        <button
          type="button"
          onClick={() => void navigate('/movimenti')}
          className="flex items-center gap-1 text-caption text-ink-2 transition-colors duration-200 hover:text-ink-1"
        >
          Vedi tutti
          <ChevronRight size={14} strokeWidth={2} aria-hidden />
        </button>
      </div>

      <Card padding="list">
        {/* Rounded to 12 inside a card rounded to 16 with 4 of padding:
            that is the radius the corner actually needs, and it keeps a
            row's hover from squaring off against the card. */}
        <ul className="overflow-hidden rounded-control divide-y divide-border-soft">
          {summary.recent.map((movement) => (
            <TransactionRow
              key={movement.id}
              movement={movement}
              onOpen={() => onOpen(movement)}
            />
          ))}
        </ul>
      </Card>
    </section>
  )
}
