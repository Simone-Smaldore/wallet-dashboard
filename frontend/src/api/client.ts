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

export const CATEGORY_COLORS = [
  'chart-1',
  'chart-2',
  'chart-3',
  'chart-4',
  'chart-5',
  'chart-6',
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

async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { method = 'GET', body } = options

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

  return options.quiet ? run() : busyWhile(run)
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
  }) => mutate<Account>('/api/accounts', 'POST', body, '/api/accounts'),

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
  ) => mutate<Account>(`/api/accounts/${id}`, 'PATCH', body, '/api/accounts'),

  /* ---- Categories ---- */

  categories: () => request<Category[]>('/api/categories'),

  createCategory: (body: {
    name: string
    kind: CategoryKind
    color: CategoryColor
    icon: string
  }) => mutate<Category>('/api/categories', 'POST', body, '/api/categories'),

  updateCategory: (
    id: number,
    body: Partial<{
      name: string
      color: CategoryColor
      icon: string
      position: number
      is_archived: boolean
    }>,
  ) => mutate<Category>(`/api/categories/${id}`, 'PATCH', body, '/api/categories'),
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
