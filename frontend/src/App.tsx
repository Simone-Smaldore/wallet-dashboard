import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router'

import { BusyOverlay } from './components/BusyOverlay'
import { ConfirmPage } from './features/auth/ConfirmPage'
import { LoginPage } from './features/auth/LoginPage'
import { SessionProvider, useSession } from './features/auth/session'
import { SystemStatus } from './features/debug/SystemStatus'
import {
  AnalisiPage,
  ContiPage,
  MovimentiPage,
  NuovoMovimentoPage,
  RiepilogoPage,
} from './features/placeholder/Placeholders'
import { ProfilePage } from './features/profile/ProfilePage'
import { AppShell } from './features/shell/AppShell'

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
              <Route path="/movimenti" element={<MovimentiPage />} />
              {/* Before /movimenti/:id, or "nuovo" would be read as an id. */}
              <Route path="/movimenti/nuovo" element={<NuovoMovimentoPage />} />
              <Route path="/conti" element={<ContiPage />} />
              <Route path="/analisi" element={<AnalisiPage />} />
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
