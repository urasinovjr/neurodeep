import HomePage from './pages/home'
import RegisterPage from './pages/register'
import LoginPage from './pages/login'
import SurveyPage from './pages/survey'
import ChatPage from './pages/chat'
import HrDashboardPage from './pages/hr-dashboard'
import AdminMethodologiesPage from './pages/admin-methodologies'
import NotFoundPage from './pages/not-found'
import { useAuth } from './shared/auth'

const PUBLIC_PATHS: readonly string[] = ['/', '/register', '/login', '/404']
const PUBLIC_PREFIXES: readonly string[] = ['/s/', '/chat/']

function isPublicPath(path: string): boolean {
  if (PUBLIC_PATHS.includes(path)) return true
  return PUBLIC_PREFIXES.some((prefix) => path.startsWith(prefix))
}

export default function App() {
  const { user, isLoading } = useAuth()
  const path = window.location.pathname

  if (isLoading) {
    return (
      <main className="page-shell">
        <p>Загрузка…</p>
      </main>
    )
  }

  if (!user && !isPublicPath(path)) {
    window.location.replace('/login')
    return null
  }

  if (path === '/') return <HomePage />
  if (path === '/register') return <RegisterPage />
  if (path === '/login') return <LoginPage />
  if (path.startsWith('/s/')) return <SurveyPage />
  if (path.startsWith('/chat/')) return <ChatPage />
  if (path === '/hr/dashboard') return <HrDashboardPage />
  if (path === '/admin/methodologies') return <AdminMethodologiesPage />
  return <NotFoundPage />
}
