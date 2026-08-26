/* Typed client for the backend.
 *
 * Same URLs in dev and in production: Vite proxies /api to uvicorn locally,
 * Vercel rewrites it to the Python function in production.
 *
 * Every foreground request goes through `request`, which raises and lowers the
 * busy counter — so BusyOverlay cannot be forgotten at a call site.
 *
 * ⚠️ Writes invalidate the cache **here**, not at the call site. A screen that
 * saves something must not also have to remember what to drop; forgetting once
 * leaves a stale list on screen that looks like a bug in the server.
 */

import { busyWhile } from './busy'
import { invalidate } from './cache'

/* ---- Closed vocabularies, mirrored from domain/vocabulary.py ---- */

export const ACCOUNT_KINDS = ['corrente', 'deposito', 'contante', 'prepagata'] as const
export type AccountKind = (typeof ACCOUNT_KINDS)[number]

export const CATEGORY_KINDS = ['expense', 'income'] as const
export type CategoryKind = (typeof CATEGORY_KINDS)[number]

export const TRANSACTION_KINDS = ['expense', 'income', 'transfer'] as const
export type TransactionKind = (typeof TRANSACTION_KINDS)[number]

/* ⚠️ Ten, matching domain/vocabulary.CATEGORY_COLORS. The first six are the
 * chart series and nothing else draws with more than those; the last four exist
 * because a list of categories is easily a dozen and they have to be told apart
 * at a glance. The two lists have to stay the same length: the server can assign
 * a colour this file does not know, and the picker would then show nothing as
 * selected. */
export const CATEGORY_COLORS = [
  'chart-1',
  'chart-2',
  'chart-3',
  'chart-4',
  'chart-5',
  'chart-6',
  'chart-7',
  'chart-8',
  'chart-9',
  'chart-10',
] as const
export type CategoryColor = (typeof CATEGORY_COLORS)[number]

/* ---- Shapes ---- */

export type Health = {
  status: 'ok' | 'degraded'
  environment: string
  database: 'ok' | 'unreachable' | 'not_configured'
  detail: string | null
}

export type CurrentUser = {
  id: number
  email: string
  display_name: string | null
  /** "name, or else email", computed server-side so no component repeats it. */
  label: string
  preferences: Record<string, unknown>
  household_id: number
  household_name: string
}

export type Account = {
  id: number
  name: string
  kind: AccountKind
  opening_balance_cents: number
  opening_date: string
  include_in_net_worth: boolean
  position: number
  is_archived: boolean
  /** Computed server-side: opening balance plus every movement. Never stored. */
  balance_cents: number
}

export type AccountList = {
  accounts: Account[]
  net_worth_cents: number
}

export type Category = {
  id: number
  name: string
  kind: CategoryKind
  color: CategoryColor
  icon: string
  position: number
  is_archived: boolean
}

export type Transaction = {
  id: number
  kind: TransactionKind
  /** `YYYY-MM-DD`. A day, not an instant: see domain/transaction.py. */
  date: string
  amount_cents: number
  description: string | null
  /** True for a row written by reconciling a balance. */
  is_adjustment: boolean

  account_id: number
  account_name: string
  counter_account_id: number | null
  counter_account_name: string | null

  category_id: number | null
  category_name: string | null
  category_kind: CategoryKind | null
  category_color: string | null
  category_icon: string | null
}

export type TransactionPage = {
  transactions: Transaction[]
  /** Pass back as `cursor` for the next page. Null when there is no next page. */
  next_cursor: string | null
}

export type TransactionFilters = {
  from?: string
  to?: string
  account_id?: number
  category_id?: number
  kind?: TransactionKind
  q?: string
  cursor?: string
}

export type ReconcileResult = {
  difference_cents: number
  /** Null when the balance already matched and nothing was written. */
  transaction: Transaction | null
  new_balance_cents: number
}

export type Household = {
  id: number
  name: string
  /** Null means no target set, which is not the same as a target of zero. */
  monthly_savings_target_cents: number | null
  /** Which income category is the salary. Null: not chosen yet. */
  salary_category_id: number | null
}

/** A month judged against the savings goal.
 *
 * ⚠️ The salary that funds a month arrived the month before: pay lands on the
 * 27th, so September is lived on August's salary and September's own salary
 * belongs to October. Only the salary shifts — a refund or a gift is spent in
 * the month it arrives, so it counts where it lands. */
export type SavingsMonth = {
  /** First day of the month this is about. */
  month: string
  /** The salary from the month before: what this month lives on. */
  salary_cents: number
  other_income_cents: number
  budget_cents: number
  spent_cents: number
  saved_cents: number
  is_open: boolean
}

export type Savings = {
  target_cents: number | null
  salary_category_id: number | null
  salary_category_name: string | null
  /** Last month: finished, so the only one that can carry a verdict. */
  closed: SavingsMonth | null
  /** This month. It gets an allowance instead. */
  open: SavingsMonth | null
  /** Null, not false, when there is nothing to judge yet. */
  met: boolean | null
  /** What can still be spent this month and still hit the target. Negative
   *  means the target is already out of reach. */
  allowance_cents: number | null
}

export type Period = { start: string; end: string }

/** ⚠️ Transfers and adjustments are in none of these. The rule lives in
 *  backend/app/domain/stats.py and arrives already applied. */
export type Totals = {
  income_cents: number
  expense_cents: number
  savings_cents: number
  /** Zero here means "nothing recorded", which the screen says in words. */
  movement_count: number
}

export type CategorySlice = {
  category_id: number | null
  /** Already resolved server-side, "Senza categoria" included. */
  name: string
  color: string | null
  icon: string | null
  total_cents: number
  /** Out of 1000, and they add up to exactly 1000. */
  share_permille: number
  previous_cents: number
  delta_cents: number
}

export type MonthPoint = {
  /** First day of the month. */
  month: string
  income_cents: number
  expense_cents: number
  savings_cents: number
  /** Net worth at the **end** of this month, not the latest one repeated. */
  net_worth_cents: number
  movement_count: number
}

export type Pace = {
  elapsed_days: number
  total_days: number
  spent_cents: number
  daily_average_cents: number
  /** ⚠️ A linear projection, not a forecast. The label has to say so. */
  projection_cents: number
}

export type Summary = {
  on: string
  period: Period
  net_worth_cents: number
  accounts: Account[]
  totals: Totals
  savings: Savings
  recent: Transaction[]
}

export type Analysis = {
  period: Period
  previous: Period
  totals: Totals
  previous_totals: Totals
  by_category: CategorySlice[]
  months: MonthPoint[]
  top_expenses: Transaction[]
  pace: Pace
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

type Options = {
  method?: string
  body?: unknown
  /** Errors this caller handles itself, so they do not read as failures. */
  quiet?: boolean
}

/** ⚠️ **The overlay is for writes.**
 *
 * It blocks the page so a save cannot be tapped twice and so you know the money
 * landed — which is why saving a movement waits for the server on purpose. A
 * read has none of that: if it fails, the screen stays as it was.
 *
 * So a GET is quiet by default. Blocking the whole app to go and fetch a list
 * of categories charges every screen the price that was meant for the one
 * gesture that matters, and it is what made the app feel slow: every cache miss
 * — every cold open, every change of period — put a full-screen scrim up.
 *
 * A screen that is loading says so itself, in its own layout. A screen that is
 * saving is held still.
 */
async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { method = 'GET', body } = options
  const quiet = options.quiet ?? method === 'GET'

  const run = async (): Promise<T> => {
    const response = await fetch(path, {
      method,
      headers: {
        accept: 'application/json',
        ...(body === undefined ? {} : { 'content-type': 'application/json' }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

    if (response.status === 204) return undefined as T

    const payload: unknown = await response.json().catch(() => null)

    if (!response.ok) {
      throw new ApiError(detailOf(payload, response.status), response.status)
    }

    if (payload === null) {
      throw new ApiError(`Risposta non leggibile da ${path}`, response.status)
    }
    return payload as T
  }

  return quiet ? run() : busyWhile(run)
}

/** Pull something readable out of an error body.
 *
 * FastAPI answers a validation error with a list of objects rather than a
 * string; showing "[object Object]" to someone who mistyped an amount would be
 * worse than saying nothing.
 */
function detailOf(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown }
      if (typeof first?.msg === 'string') return first.msg
    }
  }
  return `Richiesta fallita (HTTP ${status})`
}

export const api = {
  /** /_stato reads this one; it must never block the page behind an overlay. */
  health: () => request<Health>('/api/health', { quiet: true }),

  /* ---- Access ---- */

  /** Answers the same whether or not the address is allowed — on purpose. */
  requestLink: (email: string) =>
    request<{ message: string }>('/api/auth/request-link', {
      method: 'POST',
      body: { email },
    }),

  verify: (token: string) =>
    request<CurrentUser>('/api/auth/verify', { method: 'POST', body: { token } }),

  /** Quiet: at startup "not signed in" is an answer, not a failure. */
  me: () => request<CurrentUser>('/api/auth/me', { quiet: true }),

  updateProfile: (changes: { display_name?: string | null }) =>
    request<CurrentUser>('/api/auth/me', { method: 'PATCH', body: changes }),

  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),

  logoutAll: () => request<void>('/api/auth/logout-all', { method: 'POST' }),

  /* ---- Accounts ---- */

  accounts: () => request<AccountList>('/api/accounts'),

  createAccount: (body: {
    name: string
    kind: AccountKind
    opening_balance_cents: number
    opening_date: string
    include_in_net_worth: boolean
  }) => mutate<Account>('/api/accounts', 'POST', body, '/api/accounts', '/api/stats'),

  updateAccount: (
    id: number,
    body: Partial<{
      name: string
      kind: AccountKind
      opening_balance_cents: number
      opening_date: string
      include_in_net_worth: boolean
      position: number
      is_archived: boolean
    }>,
  ) => mutate<Account>(`/api/accounts/${id}`, 'PATCH', body, '/api/accounts', '/api/stats'),

  /* ---- Categories ---- */

  categories: () => request<Category[]>('/api/categories'),

  /** `color` and `icon` are optional: the quick-entry sheet sends the name
   *  alone and lets the server pick, so creating a category mid-movement costs
   *  one field instead of three. */
  createCategory: (body: {
    name: string
    kind: CategoryKind
    color?: CategoryColor
    icon?: string
  }) => mutate<Category>('/api/categories', 'POST', body, '/api/categories', '/api/stats'),

  updateCategory: (
    id: number,
    body: Partial<{
      name: string
      color: CategoryColor
      icon: string
      position: number
      is_archived: boolean
    }>,
  ) =>
    mutate<Category>(
      `/api/categories/${id}`,
      'PATCH',
      body,
      '/api/categories',
      '/api/stats',
    ),

  /* ---- Transactions ---- */

  transactions: (filters: TransactionFilters = {}) =>
    request<TransactionPage>(`/api/transactions${toQuery(filters)}`),

  createTransaction: (body: {
    kind: TransactionKind
    date: string
    amount_cents: number
    account_id: number
    counter_account_id?: number | null
    category_id?: number | null
    description?: string | null
  }) =>
    // A movement moves a balance, so the accounts list is stale the moment this
    // lands. Invalidating both here is what stops a screen from having to know.
    mutate<Transaction>(
      '/api/transactions',
      'POST',
      body,
      '/api/transactions',
      '/api/accounts',
      '/api/stats',
      '/api/auth/me',
    ),

  updateTransaction: (
    id: number,
    body: Partial<{
      kind: TransactionKind
      date: string
      amount_cents: number
      account_id: number
      counter_account_id: number | null
      category_id: number | null
      description: string | null
    }>,
  ) =>
    mutate<Transaction>(
      `/api/transactions/${id}`,
      'PATCH',
      body,
      '/api/transactions',
      '/api/accounts',
      '/api/stats',
    ),

  deleteTransaction: (id: number) =>
    mutate<void>(
      `/api/transactions/${id}`,
      'DELETE',
      undefined,
      '/api/transactions',
      '/api/accounts',
      '/api/stats',
    ),

  /* ---- The dashboard ---- */

  /** Everything the Riepilogo draws, in one round trip: the screen is opened
   *  several times a day against a function that starts cold. */
  summary: (on?: string) => request<Summary>(`/api/stats/summary${toQuery({ on })}`),

  analysis: (range: { from?: string; to?: string } = {}) =>
    request<Analysis>(`/api/stats/analysis${toQuery(range)}`),

  /** The months that have something in them, so the period picker can offer
   *  only the periods there is something to look at. */
  calendar: () => request<{ months: string[] }>('/api/stats/calendar'),

  /** The long charts, over a window of your choosing.
   *
   * ⚠️ Apart from `analysis` on purpose: widening a line from one year to five
   * must not re-fetch a pie, and changing the month must not re-fetch five
   * years of history. `months: 0` means everything there is. */
  series: (range: { months: number; end?: string }) =>
    request<{ months: MonthPoint[] }>(`/api/stats/series${toQuery(range)}`),

  /* ---- Household: the settings that belong to the money ---- */

  household: () => request<Household>('/api/household'),

  /** ⚠️ Sending null clears a field. Omitting it changes nothing. */
  updateHousehold: (
    body: Partial<{
      monthly_savings_target_cents: number | null
      salary_category_id: number | null
    }>,
  ) =>
    mutate<Household>('/api/household', 'PATCH', body, '/api/household', '/api/stats'),

  reconcile: (accountId: number, balance_cents: number) =>
    mutate<ReconcileResult>(
      `/api/accounts/${accountId}/reconcile`,
      'POST',
      { balance_cents },
      '/api/transactions',
      '/api/accounts',
      '/api/stats',
    ),
}

/** Turn a filter object into a query string, dropping what is not set.
 *
 * An absent filter and an empty one are the same thing here, and sending
 * `?q=` would make the backend search for the empty string. */
function toQuery(filters: Record<string, unknown>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === '') continue
    params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

async function mutate<T>(
  path: string,
  method: string,
  body: unknown,
  ...invalidates: string[]
): Promise<T> {
  const result = await request<T>(path, { method, body })
  for (const prefix of invalidates) invalidate(prefix)
  return result
}
