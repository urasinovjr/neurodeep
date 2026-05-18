import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { Button, Input, Logo } from '../../shared/ui'
import {
  PASSWORD_RULES_HINT,
  useAuth,
  validateEmail,
  validatePassword,
  validateRequired,
} from '../../shared/auth'
import type { ApiError } from '../../shared/api'

function readInviteToken(): string | null {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('invite')
  return value && value.length > 0 ? value : null
}

export default function RegisterPage() {
  const { register } = useAuth()
  const inviteToken = useMemo(() => readInviteToken(), [])

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return

    const next: Record<string, string> = {}
    const firstIssue = validateRequired(firstName, 'Имя')
    if (firstIssue) next.firstName = firstIssue
    const lastIssue = validateRequired(lastName, 'Фамилия')
    if (lastIssue) next.lastName = lastIssue
    const emailIssue = validateEmail(email)
    if (emailIssue) next.email = emailIssue
    const passwordIssue = validatePassword(password)
    if (passwordIssue) next.password = passwordIssue
    if (password !== passwordConfirm) next.passwordConfirm = 'Пароли не совпадают'

    setErrors(next)
    setFormError(null)
    if (Object.keys(next).length > 0) return

    setIsSubmitting(true)
    try {
      await register({
        email: email.trim(),
        password,
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        inviteToken,
      })
      setSubmittedEmail(email.trim())
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setFormError(apiErr?.detail ?? 'Не удалось зарегистрироваться. Попробуйте позже.')
      setIsSubmitting(false)
    }
  }

  if (submittedEmail) {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <Logo size="medium" className="auth-card__logo" />
          <h1 className="auth-card__title">Подтвердите email</h1>
          <p className="auth-form__success" role="status">
            Регистрация прошла успешно. Мы отправили ссылку для подтверждения на адрес <strong>{submittedEmail}</strong>.
          </p>
          <p className="auth-card__subtitle">
            После подтверждения email вы сможете войти в систему.
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
        <h1 className="auth-card__title">Регистрация</h1>
        <p className="auth-card__subtitle">
          {inviteToken
            ? 'Вы регистрируетесь по приглашению — после подтверждения email получите доступ HR-исследователя.'
            : 'Создайте аккаунт PsychoGraph. Доступ к рабочему кабинету предоставит администратор.'}
        </p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {formError && <p className="auth-form__error" role="alert">{formError}</p>}

          <Input
            label="Имя"
            autoComplete="given-name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            error={errors.firstName}
            disabled={isSubmitting}
            required
          />

          <Input
            label="Фамилия"
            autoComplete="family-name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            error={errors.lastName}
            disabled={isSubmitting}
            required
          />

          <Input
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={errors.email}
            disabled={isSubmitting}
            required
          />

          <Input
            label="Пароль"
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
            Зарегистрироваться
          </Button>
        </form>

        <p className="auth-card__footer">
          Уже есть аккаунт? <a href="/login">Войти</a>
        </p>
      </div>
    </main>
  )
}
