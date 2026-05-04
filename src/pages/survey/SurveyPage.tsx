export default function SurveyPage() {
  const token = window.location.pathname.replace(/^\/s\//, '')
  return (
    <main className="page-shell">
      <h1>Опрос</h1>
      <p>Анонимная сессия по invite-токену.</p>
      <p className="page-subtitle">
        Токен: <code>{token || '(не указан)'}</code>
      </p>
      <p className="page-subtitle">Заглушка — чат-опрос появится в TASK-070+.</p>
    </main>
  )
}
