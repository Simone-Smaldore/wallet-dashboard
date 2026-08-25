import { BrowserRouter, Route, Routes } from 'react-router'

import { SystemStatus } from './features/debug/SystemStatus'
import { HomePage } from './features/home/HomePage'

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />

        {/* Unlisted, and deliberately outside any session gate once one exists:
            the page is there to explain outages, and a database outage also
            blocks signing in. */}
        <Route path="/_stato" element={<SystemStatus />} />
      </Routes>
    </BrowserRouter>
  )
}
