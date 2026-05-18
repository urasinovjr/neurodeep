import HomePage from './pages/home'
import RegisterPage from './pages/register'
import LoginPage from './pages/login'
import VerifyEmailPage from './pages/verify-email'
import ForgotPasswordPage from './pages/forgot-password'
import ResetPasswordPage from './pages/reset-password'
import PendingApprovalPage from './pages/pending-approval'
import { ChatPage, ConsentPage } from './pages/respondent'
import HrDashboardPage from './pages/hr-dashboard'
import AdminMethodologiesPage from './pages/admin-methodologies'
import NotFoundPage from './pages/not-found'
import { useAuth } from './shared/auth'

const PUBLIC_PATHS: readonly string[] = [
  '/',
  '/register',
  '/login',
  '/verify-email',
  '/forgot-password',
  '/reset-password',
  '/404',
]
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

  if (user && user.role === 'pending' && path !== '/pending-approval' && path !== '/login') {
    window.location.replace('/pending-approval')
    return null
  }

  if (path === '/') return <HomePage />
  if (path === '/register') return <RegisterPage />
  if (path === '/login') return <LoginPage />
  if (path === '/verify-email') return <VerifyEmailPage />
  if (path === '/forgot-password') return <ForgotPasswordPage />
  if (path === '/reset-password') return <ResetPasswordPage />
  if (path === '/pending-approval') return <PendingApprovalPage />
  if (path.startsWith('/s/')) return <ConsentPage />
  if (path.startsWith('/chat/')) return <ChatPage />
  if (path === '/hr/dashboard') return <HrDashboardPage />
  if (path === '/admin/methodologies') return <AdminMethodologiesPage />
  return <NotFoundPage />
}
