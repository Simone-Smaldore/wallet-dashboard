/* Typed client for the backend.
 *
 * Same URLs in dev and in production: Vite proxies /api to uvicorn locally,
 * Vercel rewrites it to the Python function in production.
 *
 * Every foreground request goes through `request`, which raises and lowers the
 * busy counter — so BusyOverlay cannot be forgotten at a call site.
 */

import { busyWhile } from './busy'

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
      const detail =
        payload && typeof payload === 'object' && 'detail' in payload
          ? String((payload as { detail: unknown }).detail)
          : `Richiesta fallita (HTTP ${response.status})`
      throw new ApiError(detail, response.status)
    }

    if (payload === null) {
      throw new ApiError(`Risposta non leggibile da ${path}`, response.status)
    }
    return payload as T
  }

  return options.quiet ? run() : busyWhile(run)
}

export const api = {
  /** /_stato reads this one; it must never block the page behind an overlay. */
  health: () => request<Health>('/api/health', { quiet: true }),

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
}
