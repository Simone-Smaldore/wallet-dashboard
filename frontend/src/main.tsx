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

// No service worker registration here yet: the PWA is M5, and registering one
// before there are icons and a manifest would only cache a shell that does not
// exist.
