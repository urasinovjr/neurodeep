import { useCallback, useEffect, useState } from 'react'
import {
  clearDraft,
  EMPTY_DRAFT,
  readDraft,
  writeDraft,
  type NewSurveyDraft,
} from '../storage'

export type ValidationErrors = Partial<Record<keyof NewSurveyDraft, string>>

export const NAME_MIN = 3
export const NAME_MAX = 200
export const WELCOME_MAX = 10000
export const TOTAL_STEPS = 5

export function validateStep(
  step: number,
  draft: NewSurveyDraft,
): ValidationErrors {
  const errors: ValidationErrors = {}
  if (step === 1) {
    const trimmed = draft.name.trim()
    if (trimmed.length < NAME_MIN) {
      errors.name = `Минимум ${NAME_MIN} символа.`
    } else if (trimmed.length > NAME_MAX) {
      errors.name = `Максимум ${NAME_MAX} символов.`
    }
  } else if (step === 2) {
    if (draft.methodologyId === null) {
      errors.methodologyId = 'Выберите методику из списка.'
    }
  } else if (step === 3) {
    if (draft.startDate && draft.endDate) {
      const start = new Date(draft.startDate).getTime()
      const end = new Date(draft.endDate).getTime()
      if (Number.isNaN(start) || Number.isNaN(end)) {
        errors.endDate = 'Некорректный формат даты.'
      } else if (end <= start) {
        errors.endDate = 'Дата окончания должна быть позже даты старта.'
      }
    }
  } else if (step === 4) {
    if (draft.welcomeMessage.length > WELCOME_MAX) {
      errors.welcomeMessage = `Максимум ${WELCOME_MAX} символов.`
    }
  }
  return errors
}

export function validateAll(draft: NewSurveyDraft): ValidationErrors {
  return {
    ...validateStep(1, draft),
    ...validateStep(2, draft),
    ...validateStep(3, draft),
    ...validateStep(4, draft),
  }
}

export type UseNewSurveyForm = {
  draft: NewSurveyDraft
  errors: ValidationErrors
  setField: <K extends keyof NewSurveyDraft>(
    key: K,
    value: NewSurveyDraft[K],
  ) => void
  reset: () => void
  goNext: () => boolean
  goBack: () => void
  goToStep: (step: number) => void
}

export function useNewSurveyForm(): UseNewSurveyForm {
  const [draft, setDraft] = useState<NewSurveyDraft>(() => {
    const persisted = readDraft()
    return persisted ?? EMPTY_DRAFT
  })
  const [errors, setErrors] = useState<ValidationErrors>({})

  useEffect(() => {
    writeDraft(draft)
  }, [draft])

  const setField = useCallback(
    <K extends keyof NewSurveyDraft>(key: K, value: NewSurveyDraft[K]) => {
      setDraft((prev) => ({ ...prev, [key]: value }))
      setErrors((prev) => {
        if (!(key in prev)) return prev
        const next = { ...prev }
        delete next[key]
        return next
      })
    },
    [],
  )

  const reset = useCallback(() => {
    clearDraft()
    setDraft(EMPTY_DRAFT)
    setErrors({})
  }, [])

  const goNext = useCallback((): boolean => {
    const stepErrors = validateStep(draft.step, draft)
    if (Object.keys(stepErrors).length > 0) {
      setErrors(stepErrors)
      return false
    }
    setErrors({})
    setDraft((prev) => ({ ...prev, step: Math.min(TOTAL_STEPS, prev.step + 1) }))
    return true
  }, [draft])

  const goBack = useCallback(() => {
    setErrors({})
    setDraft((prev) => ({ ...prev, step: Math.max(1, prev.step - 1) }))
  }, [])

  const goToStep = useCallback((step: number) => {
    setErrors({})
    setDraft((prev) => ({
      ...prev,
      step: Math.max(1, Math.min(TOTAL_STEPS, step)),
    }))
  }, [])

  return { draft, errors, setField, reset, goNext, goBack, goToStep }
}
