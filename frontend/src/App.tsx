import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router'

import { BusyOverlay } from './components/BusyOverlay'
import { ConfirmPage } from './features/auth/ConfirmPage'
import { LoginPage } from './features/auth/LoginPage'
import { SessionProvider, useSession } from './features/auth/session'
import { SystemStatus } from './features/debug/SystemStatus'
import { AccountsPage } from './features/accounts/AccountsPage'
import { CategoriesPage } from './features/accounts/CategoriesPage'
import { RiepilogoPage } from './features/dashboard/RiepilogoPage'
import { TransactionsPage } from './features/transactions/TransactionsPage'
import { ProfilePage } from './features/profile/ProfilePage'
import { AppShell } from './features/shell/AppShell'

/** ⚠️ Analisi is loaded on demand, and it is the only screen that is.
 *
 * Recharts is 120 kB gzipped — more than the whole app was before it — and it
 * is used by exactly one route. Bundled in, that weight would land on the
 * quick-entry screen too: the one used standing at a till, where the first
 * priority of this product is that recording a spend costs three taps and no
 * waiting. Charts are looked at once a month, from a sofa, and can afford to
 * fetch themselves.
 */
const AnalisiPage = lazy(async () => ({
  default: (await import('./features/analysis/AnalisiPage')).AnalisiPage,
}))

export function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        {/* Outside the routes: a pending request must block whatever is shown. */}
        <BusyOverlay />
        <Routes>
          <Route path="/accedi" element={<LoginPage />} />
          <Route path="/accedi/conferma" element={<ConfirmPage />} />

          {/* Unlisted, and deliberately outside RequireSession: the page exists
              to explain outages, and a database outage also blocks signing in. */}
          <Route path="/_stato" element={<SystemStatus />} />

          <Route element={<RequireSession />}>
            <Route element={<AppShell />}>
              <Route path="/riepilogo" element={<RiepilogoPage />} />
              <Route path="/movimenti" element={<TransactionsPage />} />
              <Route path="/conti" element={<AccountsPage />} />
              <Route path="/categorie" element={<CategoriesPage />} />
              <Route
                path="/analisi"
                element={
                  // Nothing rather than a spinner: the chunk arrives in a
                  // frame or two on any connection that got you this far, and
                  // a flash of "Attendi…" reads as a fault.
                  <Suspense fallback={<div className="min-h-full bg-bg-app" />}>
                    <AnalisiPage />
                  </Suspense>
                }
              />
              <Route path="/profilo" element={<ProfilePage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/riepilogo" replace />} />
        </Routes>
      </SessionProvider>
    </BrowserRouter>
  )
}

/** Everything that is not the login screen or the status page sits behind this.
 *
 * While the startup check is in flight it renders nothing rather than the login
 * screen: bouncing a signed-in user to /accedi for a frame and back is worse
 * than a blank moment, and on a cold Neon database that frame can last seconds.
 */
function RequireSession() {
  const { user, loading } = useSession()

  if (loading) return <div className="min-h-full bg-bg-app" />
  if (!user) return <Navigate to="/accedi" replace />
  return <Outlet />
}
