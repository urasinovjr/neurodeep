import { useState } from 'react'
import { Button } from '../../shared/ui'
import StepDates from './components/StepDates'
import StepMethodology from './components/StepMethodology'
import StepName from './components/StepName'
import StepProgress from './components/StepProgress'
import StepReview from './components/StepReview'
import StepWelcome from './components/StepWelcome'
import { createSurvey } from './api/newSurveyApi'
import type { SurveyCreateRequestDto } from './api/newSurvey.dto'
import { useMethodologies } from './hooks/useMethodologies'
import {
  TOTAL_STEPS,
  useNewSurveyForm,
  validateAll,
} from './hooks/useNewSurveyForm'
import { clearDraft } from './storage'
import './new-survey.css'

type ApiError = { status?: number; detail?: string }

function toIsoOrNull(value: string): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}

export default function NewSurveyPage() {
  const form = useNewSurveyForm()
  const methodologiesState = useMethodologies()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)

  const { draft, errors } = form
  const step = draft.step

  async function handleSubmit(): Promise<void> {
    const allErrors = validateAll(draft)
    if (Object.keys(allErrors).length > 0) {
      setSubmitError('Заполните обязательные поля и проверьте даты.')
      return
    }
    setSubmitError(null)
    setIsSubmitting(true)
    try {
      const payload: SurveyCreateRequestDto = {
        methodology_id: draft.methodologyId!,
        name: draft.name.trim(),
        welcome_message: draft.welcomeMessage.trim() || null,
        start_date: toIsoOrNull(draft.startDate),
        end_date: toIsoOrNull(draft.endDate),
        allow_individual_share: draft.allowIndividualShare,
      }
      const created = await createSurvey(payload)
      clearDraft()
      window.location.href = `/hr/surveys/${created.id}`
    } catch (err: unknown) {
      const apiErr = err as ApiError
      setSubmitError(apiErr.detail ?? 'Не удалось создать исследование.')
      setIsSubmitting(false)
    }
  }

  function renderStep() {
    if (step === 1) {
      return (
        <StepName
          value={draft.name}
          error={errors.name}
          onChange={(value) => form.setField('name', value)}
        />
      )
    }
    if (step === 2) {
      return (
        <StepMethodology
          methodologies={methodologiesState.methodologies}
          isLoading={methodologiesState.isLoading}
          loadError={methodologiesState.error}
          selectedId={draft.methodologyId}
          error={errors.methodologyId}
          onSelect={(id) => form.setField('methodologyId', id)}
        />
      )
    }
    if (step === 3) {
      return (
        <StepDates
          startDate={draft.startDate}
          endDate={draft.endDate}
          endError={errors.endDate}
          onStart={(value) => form.setField('startDate', value)}
          onEnd={(value) => form.setField('endDate', value)}
        />
      )
    }
    if (step === 4) {
      return (
        <StepWelcome
          welcomeMessage={draft.welcomeMessage}
          allowIndividualShare={draft.allowIndividualShare}
          welcomeError={errors.welcomeMessage}
          onMessage={(value) => form.setField('welcomeMessage', value)}
          onAllowShare={(value) =>
            form.setField('allowIndividualShare', value)
          }
        />
      )
    }
    return (
      <StepReview
        draft={draft}
        methodologies={methodologiesState.methodologies}
      />
    )
  }

  return (
    <main className="new-survey-page">
      <div className="new-survey-shell">
        <header className="new-survey-header">
          <a className="back-link" href="/hr/dashboard">
            ← К дашборду
          </a>
          <h1>Новое исследование</h1>
          <p className="page-hint">
            Заполните 5 шагов. Черновик автоматически сохраняется в этом
            браузере — можно вернуться позже.
          </p>
        </header>

        <StepProgress step={step} onStepClick={form.goToStep} />

        <section className="new-survey-card">{renderStep()}</section>

        {submitError ? <p className="step-error step-error-banner">{submitError}</p> : null}

        <footer className="new-survey-footer">
          {step > 1 ? (
            <Button type="button" variant="secondary" onClick={form.goBack}>
              ← Назад
            </Button>
          ) : (
            <button
              type="button"
              className="text-button"
              onClick={() => {
                if (window.confirm('Очистить черновик и начать с нуля?')) {
                  form.reset()
                }
              }}
            >
              Очистить
            </button>
          )}
          {step < TOTAL_STEPS ? (
            <Button type="button" variant="primary" onClick={form.goNext}>
              Далее →
            </Button>
          ) : (
            <Button
              type="button"
              variant="primary"
              isLoading={isSubmitting}
              onClick={() => void handleSubmit()}
            >
              Создать исследование
            </Button>
          )}
        </footer>
      </div>
    </main>
  )
}
