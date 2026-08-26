import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import './styles/index.css'

const container = document.getElementById('root')
if (!container) {
  throw new Error('Elemento #root non trovato in index.html')
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// ⚠️ The service worker is registered **only in production**. In development it
// would serve yesterday's bundle and every change would look like it had not
// been applied — half an hour lost to a bug that is not there.
//
// Registered after load so it never competes for bandwidth with the app itself
// on the first visit, which is the one visit where speed is noticed.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // An app that works is worth more than an app that is installable. A
      // failed registration must not be visible.
    })
  })
}
