import { useEffect, useState } from 'react'
import './App.css'

type HealthStatus = 'loading' | 'ok' | 'error'

const HEALTH_LABELS: Record<HealthStatus, string> = {
  loading: 'проверяется…',
  ok: 'OK',
  error: 'недоступен',
}

export default function App() {
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
  const [status, setStatus] = useState<HealthStatus>('loading')

  useEffect(() => {
    let active = true
    async function check() {
      try {
        const response = await fetch(`${apiBase}/health`)
        if (!active) return
        setStatus(response.ok ? 'ok' : 'error')
      } catch {
        if (!active) return
        setStatus('error')
      }
    }
    void check()
    return () => {
      active = false
    }
  }, [apiBase])

  return (
    <main className="app-shell">
      <h1>PsychoGraph</h1>
      <p>Веб-платформа психологической диагностики через чат с NLP-анализом.</p>
      <p className="app-subtitle">Каркас инициализирован. Реализация UI — в TASK-060 и далее.</p>
      <p className={`app-health app-health--${status}`}>
        Статус backend: <strong>{HEALTH_LABELS[status]}</strong>
      </p>
      <p className="app-api-base">
        API base URL: <code>{apiBase}</code>
      </p>
    </main>
  )
}
