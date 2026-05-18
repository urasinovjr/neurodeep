import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { Button, Input, Logo } from '../../shared/ui'
import { PASSWORD_RULES_HINT, useAuth, validatePassword } from '../../shared/auth'
import type { ApiError } from '../../shared/api'

function readToken(): string | null {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('token')
  return value && value.length > 0 ? value : null
}

export default function ResetPasswordPage() {
  const { resetPassword } = useAuth()
  const token = useMemo(() => readToken(), [])

  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDone, setIsDone] = useState(false)

  if (!token) {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <Logo size="medium" className="auth-card__logo" />
          <h1 className="auth-card__title">Смена пароля</h1>
          <p className="auth-form__error" role="alert">
            В ссылке отсутствует токен. Запросите восстановление пароля заново.
          </p>
          <p className="auth-card__footer">
            <a href="/forgot-password">Запросить новую ссылку</a>
          </p>
        </div>
      </main>
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const next: Record<string, string> = {}
    const passwordIssue = validatePassword(password)
    if (passwordIssue) next.password = passwordIssue
    if (password !== passwordConfirm) next.passwordConfirm = 'Пароли не совпадают'

    setErrors(next)
    setFormError(null)
    if (Object.keys(next).length > 0) return

    setIsSubmitting(true)
    try {
      await resetPassword(token!, password)
      setIsDone(true)
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setFormError(apiErr?.detail ?? 'Не удалось сменить пароль. Запросите ссылку заново.')
      setIsSubmitting(false)
    }
  }

  if (isDone) {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <Logo size="medium" className="auth-card__logo" />
          <h1 className="auth-card__title">Пароль обновлён</h1>
          <p className="auth-form__success" role="status">
            Пароль успешно изменён. Войдите с новым паролем.
          </p>
          <p className="auth-card__footer">
            <a href="/login">Перейти ко входу</a>
          </p>
        </div>
      </main>
    )
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <Logo size="medium" className="auth-card__logo" />
        <h1 className="auth-card__title">Новый пароль</h1>
        <p className="auth-card__subtitle">Придумайте новый пароль для входа.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {formError && <p className="auth-form__error" role="alert">{formError}</p>}

          <Input
            label="Новый пароль"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={errors.password}
            disabled={isSubmitting}
            required
          />

          <p className="auth-form__hint">{PASSWORD_RULES_HINT}</p>

          <Input
            label="Повторите пароль"
            type="password"
            autoComplete="new-password"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            error={errors.passwordConfirm}
            disabled={isSubmitting}
            required
          />

          <Button type="submit" size="large" isLoading={isSubmitting}>
            Сохранить пароль
          </Button>
        </form>
      </div>
    </main>
  )
}
