/* Typed client for the backend.
 *
 * Same URLs in dev and in production: Vite proxies /api to uvicorn locally,
 * Vercel rewrites it to the Python function in production.
 *
 * Small on purpose at M0. The read cache (api/cache.ts) arrives with the first
 * screen that reads real data.
 */

export type Health = {
  status: 'ok' | 'degraded'
  environment: string
  database: 'ok' | 'unreachable' | 'not_configured'
  detail: string | null
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { accept: 'application/json' } })

  // 503 from /api/health is an answer, not a failure: it carries the payload
  // that says what is broken. Only a response with no JSON body is an error.
  const body: unknown = await response.json().catch(() => null)
  if (body === null) {
    throw new Error(`Risposta non leggibile da ${path} (HTTP ${response.status})`)
  }

  return body as T
}

export const api = {
  health: () => request<Health>('/api/health'),
}
