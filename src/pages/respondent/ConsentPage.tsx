import { useId } from 'react'
import { Button } from '../../shared/ui'
import {
  CONSENT_CHECKBOX_LABEL,
  CONSENT_INTRO,
  CONSENT_POINTS,
  CONSENT_TITLE,
} from './consentText'
import { useConsentFlow } from './hooks/useConsentFlow'
import './consent.css'

function describeFailure(status: number | null): {
  title: string
  body: string
} {
  if (status === 404) {
    return {
      title: 'Опрос не найден',
      body: 'Проверьте ссылку: возможно, она содержит ошибку.',
    }
  }
  if (status === 410) {
    return {
      title: 'Опрос недоступен',
      body: 'Срок прохождения истёк или опрос был закрыт.',
    }
  }
  return {
    title: 'Не удалось открыть опрос',
    body: 'Попробуйте обновить страницу или вернитесь к ссылке позже.',
  }
}

export default function ConsentPage() {
  const flow = useConsentFlow()
  const checkboxId = useId()

  if (flow.isLoadingPreview) {
    return (
      <main className="consent-page">
        <div className="consent-shell">
          <section className="consent-loading">Загрузка опроса…</section>
        </div>
      </main>
    )
  }

  if (flow.loadError || !flow.preview) {
    const failure = describeFailure(flow.loadErrorStatus)
    return (
      <main className="consent-page">
        <div className="consent-shell">
          <section className="consent-failure">
            <p className="consent-failure-title">{failure.title}</p>
            <p className="consent-failure-detail">{failure.body}</p>
          </section>
        </div>
      </main>
    )
  }

  const { preview } = flow

  return (
    <main className="consent-page">
      <div className="consent-shell">
        <section className="consent-header">
          <h1 className="consent-methodology-name">{preview.methodology.name}</h1>
          <p className="consent-methodology-meta">
            Вопросов в опросе: {preview.methodology.totalQuestions}
          </p>
          {preview.welcomeMessage ? (
            <p className="consent-welcome">{preview.welcomeMessage}</p>
          ) : null}
        </section>

        <section className="consent-card">
          {flow.restartAvailable ? (
            <>
              <h2 className="consent-title">Сессия завершена</h2>
              <p className="consent-intro">
                Предыдущая попытка прохождения была прервана. Чтобы пройти опрос
                заново, начните с нового согласия.
              </p>
              <Button
                type="button"
                variant="primary"
                size="large"
                onClick={flow.restart}
              >
                Начать заново
              </Button>
            </>
          ) : (
            <>
              <h2 className="consent-title">{CONSENT_TITLE}</h2>
              <p className="consent-intro">{CONSENT_INTRO}</p>
              {flow.restoredSessionId ? (
                <p className="consent-resume-hint">
                  Сессия уже начата ранее — после согласия вы продолжите с того же
                  места.
                </p>
              ) : null}
              <ol className="consent-points">
                {CONSENT_POINTS.map((point) => (
                  <li key={point.title}>
                    <span className="consent-point-title">{point.title}.</span>{' '}
                    <span className="consent-point-body">{point.body}</span>
                  </li>
                ))}
              </ol>

              <div className="consent-checkbox-row">
                <input
                  id={checkboxId}
                  type="checkbox"
                  checked={flow.isAccepted}
                  onChange={(event) => flow.setAccepted(event.target.checked)}
                />
                <label htmlFor={checkboxId} className="consent-checkbox-label">
                  {CONSENT_CHECKBOX_LABEL}
                </label>
              </div>

              {flow.submitError ? (
                <p className="consent-error">{flow.submitError}</p>
              ) : null}

              <Button
                type="button"
                variant="primary"
                size="large"
                onClick={() => void flow.submit()}
                disabled={!flow.isAccepted || flow.isSubmitting}
                isLoading={flow.isSubmitting}
              >
                Продолжить
              </Button>
            </>
          )}
        </section>
      </div>
    </main>
  )
}
