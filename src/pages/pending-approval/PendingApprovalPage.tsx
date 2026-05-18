import { Button, Logo } from '../../shared/ui'
import { useAuth } from '../../shared/auth'

export default function PendingApprovalPage() {
  const { user, logout } = useAuth()

  async function handleLogout() {
    await logout()
    window.location.href = '/login'
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <Logo size="medium" className="auth-card__logo" />
        <h1 className="auth-card__title">Ожидание подтверждения</h1>
        <p className="auth-card__subtitle">
          {user
            ? `${user.firstName}, ваш аккаунт ${user.email} ожидает подтверждения email и одобрения администратором.`
            : 'Аккаунт ожидает подтверждения email и одобрения администратором.'}
        </p>
        <p className="auth-card__subtitle">
          Проверьте почту — мы отправили ссылку для подтверждения. После подтверждения и назначения роли вы получите доступ к рабочему кабинету.
        </p>

        {user && (
          <Button type="button" variant="secondary" onClick={handleLogout}>
            Выйти
          </Button>
        )}

        <p className="auth-card__footer">
          <a href="/login">Вернуться ко входу</a>
        </p>
      </div>
    </main>
  )
}
