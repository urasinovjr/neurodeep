import { useState } from 'react'
import type { FormEvent } from 'react'

import { Button, Input, Logo } from '../../shared/ui'
import { useAuth, validateEmail } from '../../shared/auth'
import type { ApiError } from '../../shared/api'

export default function ForgotPasswordPage() {
  const { requestPasswordReset } = useAuth()
  const [email, setEmail] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSent, setIsSent] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const issue = validateEmail(email)
    setEmailError(issue)
    setFormError(null)
    if (issue) return

    setIsSubmitting(true)
    try {
      await requestPasswordReset(email.trim())
      setIsSent(true)
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setFormError(apiErr?.detail ?? 'Не удалось отправить ссылку. Попробуйте позже.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <Logo size="medium" className="auth-card__logo" />
        <h1 className="auth-card__title">Восстановление пароля</h1>
        <p className="auth-card__subtitle">
          Введите email — пришлём ссылку для смены пароля.
        </p>

        {isSent ? (
          <>
            <p className="auth-form__success" role="status">
              Если такой email зарегистрирован, мы отправили на него ссылку для восстановления пароля.
            </p>
            <p className="auth-card__footer">
              <a href="/login">Вернуться ко входу</a>
            </p>
          </>
        ) : (
          <>
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

              <Button type="submit" size="large" isLoading={isSubmitting}>
                Отправить ссылку
              </Button>
            </form>

            <p className="auth-card__footer">
              Вспомнили пароль? <a href="/login">Войти</a>
            </p>
          </>
        )}
      </div>
    </main>
  )
}
