import { useEffect, useMemo, useState } from 'react'

import { Logo } from '../../shared/ui'
import { useAuth } from '../../shared/auth'
import type { ApiError } from '../../shared/api'

type VerificationState = 'pending' | 'success' | 'error'

function readToken(): string | null {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('token')
  return value && value.length > 0 ? value : null
}

export default function VerifyEmailPage() {
  const { verifyEmail } = useAuth()
  const token = useMemo(() => readToken(), [])
  const [state, setState] = useState<VerificationState>(token ? 'pending' : 'error')
  const [errorDetail, setErrorDetail] = useState<string | null>(
    token ? null : 'В ссылке отсутствует токен подтверждения.',
  )

  useEffect(() => {
    if (!token) return
    let active = true
    async function run() {
      try {
        await verifyEmail(token!)
        if (!active) return
        setState('success')
      } catch (err: unknown) {
        if (!active) return
        const apiErr = err as ApiError
        setErrorDetail(apiErr?.detail ?? 'Не удалось подтвердить email.')
        setState('error')
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [token, verifyEmail])

  return (
    <main className="auth-page">
      <div className="auth-card">
        <Logo size="medium" className="auth-card__logo" />
        <h1 className="auth-card__title">Подтверждение email</h1>

        {state === 'pending' && (
          <p className="auth-card__subtitle">Подтверждаем ваш email, подождите…</p>
        )}

        {state === 'success' && (
          <>
            <p className="auth-form__success" role="status">
              Email успешно подтверждён.
            </p>
            <p className="auth-card__footer">
              <a href="/login">Перейти ко входу</a>
            </p>
          </>
        )}

        {state === 'error' && (
          <>
            <p className="auth-form__error" role="alert">
              {errorDetail ?? 'Не удалось подтвердить email.'}
            </p>
            <p className="auth-card__footer">
              <a href="/login">Вернуться ко входу</a>
            </p>
          </>
        )}
      </div>
    </main>
  )
}
