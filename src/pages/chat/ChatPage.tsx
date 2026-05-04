export default function ChatPage() {
  const sessionId = window.location.pathname.replace(/^\/chat\//, '')
  return (
    <main className="page-shell">
      <h1>Чат-опрос</h1>
      <p>Прохождение методики через чат-интерфейс.</p>
      <p className="page-subtitle">
        Сессия: <code>{sessionId || '(не указана)'}</code>
      </p>
      <p className="page-subtitle">Заглушка — диалог с вопросами появится в TASK-072+.</p>
    </main>
  )
}
