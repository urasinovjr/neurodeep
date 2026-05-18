import { useState } from 'react'
import type { FormEvent } from 'react'

import { Button, Input, Logo } from '../../shared/ui'
import { useAuth, validateEmail } from '../../shared/auth'
import type { User } from '../../shared/auth'
import type { ApiError } from '../../shared/api'

function destinationFor(user: User): string {
  if (user.role === 'admin') return '/admin/methodologies'
  if (user.role === 'researcher') return '/hr/dashboard'
  if (user.role === 'pending') return '/pending-approval'
  return '/'
}

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const emailIssue = validateEmail(email)
    const passwordIssue = password.trim() ? null : 'Введите пароль'
    setEmailError(emailIssue)
    setPasswordError(passwordIssue)
    setFormError(null)
    if (emailIssue || passwordIssue) return

    setIsSubmitting(true)
    try {
      const user = await login(email.trim(), password)
      window.location.href = destinationFor(user)
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setFormError(apiErr?.detail ?? 'Не удалось войти. Попробуйте позже.')
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <Logo size="medium" className="auth-card__logo" />
        <h1 className="auth-card__title">Вход в систему</h1>
        <p className="auth-card__subtitle">Войдите, чтобы продолжить работу с PsychoGraph</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {formError && <p className="auth-form__error" role="alert">{formError}</p>}

          <Input
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={emailError ?? undefined}
            disabled={isSubmitting}
            required
          />

          <Input
            label="Пароль"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={passwordError ?? undefined}
            disabled={isSubmitting}
            required
          />

          <Button type="submit" size="large" isLoading={isSubmitting}>
            Войти
          </Button>
        </form>

        <p className="auth-card__footer">
          <a href="/forgot-password">Забыли пароль?</a>
        </p>
        <p className="auth-card__footer">
          Нет аккаунта? <a href="/register">Зарегистрироваться</a>
        </p>
      </div>
    </main>
  )
}
