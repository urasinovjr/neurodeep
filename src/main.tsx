import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AuthProvider } from './shared/auth'
import './shared/ui/tokens.css'
import './index.css'
import './shared/ui/pages.css'

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Root element не найден')
}

createRoot(rootElement).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
