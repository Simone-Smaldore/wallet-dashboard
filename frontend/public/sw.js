/* Wallet — service worker.
 *
 * Written by hand rather than generated. `vite-plugin-pwa` would bring Workbox
 * plus a build integration to solve problems this app does not have: there is
 * one shell, one folder of hashed assets, and no offline behaviour to speak of.
 * A hundred lines including these comments is cheaper than a dependency that
 * has to be understood before it can be trusted with a cache.
 *
 * ⚠️ **Offline is not a goal here, and offline entry least of all.** It was
 * considered for V1 and dropped: a local queue of movements waiting for the
 * network is the most delicate piece in the whole project — duplicates,
 * conflicts, rows that cannot be edited until they have an id — and it is not
 * something to build before the app exists. All this file does is serve the
 * shell so the app opens, instead of the browser's dinosaur, and then the app
 * says for itself that there is no network.
 *
 * If precache manifests and update prompts are ever needed, throw this away and
 * take the library. Do not grow it into one.
 */

// ⚠️ Bump on every deploy that changes what is cached. Old caches are deleted
// on activate, so this is also how a stale shell gets thrown away.
const VERSION = 'wallet-v1'

const SHELL = `${VERSION}-shell`
const ASSETS = `${VERSION}-assets`
const OURS = [SHELL, ASSETS]

/** The page every navigation falls back to. It is a SPA: one document, and the
 *  router decides the rest. */
const SHELL_URL = '/index.html'

self.addEventListener('install', (event) => {
  // Take the shell now, so the very first offline open already works.
  event.waitUntil(
    caches.open(SHELL).then((cache) => cache.add(SHELL_URL)),
  )
  // No waiting for every tab to close: this worker only caches static files,
  // so an immediate swap cannot leave two versions disagreeing about data.
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(names.filter((name) => !OURS.includes(name)).map((name) => caches.delete(name))),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)

  // Only GET. A POST is a write, and a write is never something to replay.
  if (request.method !== 'GET') return

  // ⚠️ Anything on another origin is left entirely alone — Google Fonts
  // included. Caching a cross-origin response means storing an opaque one,
  // which cannot be inspected, cannot be validated, and counts against quota by
  // a padded size. Without the network the font simply falls back to the system
  // stack, which is what the stack is for.
  if (url.origin !== self.location.origin) return

  // ⚠️⚠️ THE API IS NEVER TOUCHED. NOT ONE ENDPOINT.
  //
  // These responses are authenticated, and in this app they are the complete
  // picture of someone's finances. A cache outlives a session: storing them
  // would mean serving the balances of a closed session to whoever opens the
  // app next. The read cache the app does have lives in api/cache.ts and is in
  // memory — it dies with the page, which is exactly the point.
  if (url.pathname.startsWith('/api/')) return

  if (request.mode === 'navigate') {
    event.respondWith(networkThenShell(request))
    return
  }

  if (url.pathname.startsWith('/assets/')) {
    // Vite puts a content hash in these names, so a cached one can never be
    // stale: a changed file is a different URL.
    event.respondWith(cacheThenNetwork(request, ASSETS))
    return
  }

  // Icons, the manifest: served from the cache and refreshed behind it.
  event.respondWith(cacheThenRevalidate(request, SHELL))
})

/** Navigations: the network decides, the cache catches the fall.
 *
 * Network first and not cache first, because the shell references the hashed
 * bundle by name: serving yesterday's shell to someone who is online would load
 * yesterday's app until the cache happened to update. */
async function networkThenShell(request) {
  try {
    const response = await fetch(request)
    // Keep the shell fresh for the next offline open.
    const cache = await caches.open(SHELL)
    cache.put(SHELL_URL, response.clone())
    return response
  } catch {
    const cached = await caches.match(SHELL_URL)
    // If even the shell is missing there is nothing honest left to serve, so
    // the browser's own error is the right answer.
    return cached ?? Response.error()
  }
}

async function cacheThenNetwork(request, cacheName) {
  const cached = await caches.match(request)
  if (cached) return cached

  const response = await fetch(request)
  if (response.ok) {
    const cache = await caches.open(cacheName)
    cache.put(request, response.clone())
  }
  return response
}

async function cacheThenRevalidate(request, cacheName) {
  const cached = await caches.match(request)

  const fresh = fetch(request)
    .then(async (response) => {
      if (response.ok) {
        const cache = await caches.open(cacheName)
        cache.put(request, response.clone())
      }
      return response
    })
    .catch(() => cached)

  return cached ?? fresh
}
