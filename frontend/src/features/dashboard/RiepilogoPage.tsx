import { useState } from 'react'
import { ChevronRight, Pencil } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { useQuery } from '../../api/cache'
import { api, type Account, type Summary } from '../../api/client'
import { Amount } from '../../components/Amount'
import { Button } from '../../components/Button'
import { AccountIcon } from '../../components/AccountIcon'
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

      <Patrimonio worth={data.net_worth} />

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

/** What you have, and how much of it you could actually spend.
 *
 * ⚠️ **Liquid and invested are separated because they get confused.** A BTP
 * maturing in 2072 is yours; it is not money for this week. One number for both
 * answers neither question well.
 *
 * ⚠️ **The invested figure carries the day it was true.** Prices are fetched
 * once a day and a market can be shut: a total that looks current and is three
 * weeks old is worse than no total — on a missing number you check, on a stale
 * one you rely.
 */
function Patrimonio({ worth }: { worth: Summary['net_worth'] }) {
  return (
    <Card>
      <p className="text-micro uppercase text-ink-3">Patrimonio</p>
      <p className="num mt-1 text-hero text-ink-1">{formatMoney(worth.total_cents)}</p>

      {worth.invested_cents === 0 ? null : (
        <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
          <div className="flex items-baseline gap-2">
            <dt className="text-caption text-ink-2">Liquido</dt>
            <dd className="num text-body text-ink-1">{formatMoney(worth.liquid_cents)}</dd>
          </div>
          <div className="flex items-baseline gap-2">
            <dt className="text-caption text-ink-2">Investito</dt>
            <dd className="num text-body text-ink-1">{formatMoney(worth.invested_cents)}</dd>
          </div>
        </dl>
      )}

      <p className="mt-2 text-caption text-ink-3">
        {worth.valued_on
          ? `Investimenti valutati al ${formatDayShort(worth.valued_on)}.`
          : null}{' '}
        {/* ⚠️ Visible, not tucked into a footer. The app describes what happened
            to your money; it does not tell you what to do with it. */}
        Wallet descrive, non consiglia.
      </p>
    </Card>
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

/** The savings goal, month by month.
 *
 * ⚠️ **The salary that funds a month arrived the month before.** Pay lands on
 * the 27th, so September is lived on August's salary and September's own salary
 * belongs to October. Without that shift the month you are in looks broke for
 * twenty-six days and rich on the twenty-seventh, and a verdict on it would say
 * nothing about how the month actually went. Only the salary moves: a refund or
 * a gift is spent where it lands.
 *
 * The verdict belongs to **last month**, the only one whose spending is
 * finished. This month gets an allowance instead — what can still be spent and
 * still land on the target — which is the one number on this screen you can
 * still do something about.
 *
 * ⚠️ Every state that is missing something says which thing, in words. No
 * target, no salary category, no month to judge yet: three different reasons
 * for an empty card, and three different sentences. A bar at zero would be the
 * same picture for all of them and true for none.
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
        <Allowance month={open} target={target} allowance={allowance} />
      ) : null}

      {closed !== null && target !== null ? (
        <p className="mt-3 border-t border-border-soft pt-3 text-caption text-ink-2">
          {met ? '✓ ' : ''}A {formatMonth(closed.month)} avevi{' '}
          <span className="num text-ink-1">{formatMoney(closed.budget_cents)}</span>, ne hai
          spesi <span className="num text-ink-1">{formatMoney(closed.spent_cents)}</span>:
          da parte <span className="num text-ink-1">{formatMoney(closed.saved_cents)}</span>{' '}
          su <span className="num">{formatMoney(target)}</span>.
        </p>
      ) : null}
    </Card>
  )
}

/** What last month decided. */
function Verdict({ summary }: { summary: Summary }) {
  const { target_cents: target, salary_category_id: salaryId, closed, met } =
    summary.savings

  if (target === null) {
    return (
      <p className="mt-2 text-body text-ink-2">
        Non ne hai impostato uno. Se ti dai una cifra, qui vedrai quanto puoi ancora
        spendere questo mese.
      </p>
    )
  }

  if (salaryId === null) {
    return (
      <p className="mt-2 text-body text-ink-2">
        Dimmi quale categoria è lo stipendio: il mese si vive con lo stipendio arrivato il
        mese prima, e senza saperlo il conto non sta in piedi.
      </p>
    )
  }

  if (closed === null) {
    return (
      <p className="mt-2 text-body text-ink-2">
        Aspetto la fine del mese: il verdetto è sul mese chiuso, l'unico la cui spesa è
        finita.
      </p>
    )
  }

  return (
    <p className={`mt-1 text-title ${met ? 'text-money-income' : 'text-money-expense'}`}>
      {met ? 'Obiettivo raggiunto' : 'Obiettivo mancato'}
    </p>
  )
}

/** What is left to spend this month.
 *
 * ⚠️ The bar fills with what has been spent against what was spendable — budget
 * minus target — so "full" means "you are at the line", not "well done".
 */
function Allowance({
  month,
  target,
  allowance,
}: {
  month: Summary['savings']['open'] & object
  target: number
  allowance: number
}) {
  // What was there to spend: the budget, minus the target you have to keep,
  // minus whatever has already gone into an investment.
  const spendable = month.budget_cents - target - Math.max(month.set_aside_cents, 0)
  const used = spendable > 0 ? Math.min(100, (month.spent_cents / spendable) * 100) : 100
  const over = allowance < 0

  return (
    <div className="mt-3">
      <p className="num text-hero text-ink-1">{formatMoney(Math.abs(allowance))}</p>
      <p className="mt-1 text-caption text-ink-2">
        {over
          ? `oltre l'obiettivo di ${formatMonth(month.month)}`
          : `puoi ancora spenderli entro ${formatMonth(month.month)}`}
      </p>

      <div className="mt-3 h-2 overflow-hidden rounded-pill bg-surface-card-2">
        <div
          className={`h-full rounded-pill ${over ? 'bg-money-expense' : 'bg-accent'}`}
          style={{ width: `${used}%` }}
        />
      </div>
      <p className="mt-2 text-caption text-ink-3">
        <span className="num">{formatMoney(month.spent_cents)}</span> spesi su{' '}
        <span className="num">{formatMoney(Math.max(spendable, 0))}</span> spendibili
        {month.salary_cents > 0 ? (
          <>
            {' '}· budget <span className="num">{formatMoney(month.budget_cents)}</span>, con
            lo stipendio del mese scorso
          </>
        ) : null}
      </p>

      {/* ⚠️ Said out loud, because it is the line that explains an otherwise
          baffling number. A month with a 10.000 € bond purchase looks like a
          disaster until it says that the money was put away, not spent. */}
      {month.set_aside_cents !== 0 ? (
        <p className="mt-1 text-caption text-ink-3">
          di cui <span className="num">{formatMoney(Math.abs(month.set_aside_cents))}</span>{' '}
          {month.set_aside_cents > 0 ? 'messi da parte' : 'ripresi dagli investimenti'} —
          fuori dal budget, dentro al patrimonio
        </p>
      ) : null}
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
              className="flex items-center gap-3 rounded-card border border-border-soft bg-surface-card p-4 shadow-card transition-colors duration-200 hover:bg-surface-hover"
            >
              <AccountIcon kind={account.kind} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-caption text-ink-2">{account.name}</p>
                {/* ⚠️ For an investment, what it is worth — not what was paid
                    in. Same field the Conti screen reads, so the two cannot
                    disagree. */}
                <p
                  className={`num text-heading ${
                    (account.value_cents ?? account.balance_cents) < 0
                      ? 'text-money-expense'
                      : 'text-ink-1'
                  }`}
                >
                  {formatMoney(account.value_cents ?? account.balance_cents)}
                </p>
              </div>
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
