const DRAFT_KEY = 'psychograph_new_survey_draft'

export type NewSurveyDraft = {
  step: number
  name: string
  methodologyId: number | null
  startDate: string
  endDate: string
  welcomeMessage: string
  allowIndividualShare: boolean
}

export const EMPTY_DRAFT: NewSurveyDraft = {
  step: 1,
  name: '',
  methodologyId: null,
  startDate: '',
  endDate: '',
  welcomeMessage: '',
  allowIndividualShare: false,
}

function isValidDraft(value: unknown): value is NewSurveyDraft {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.step === 'number' &&
    typeof record.name === 'string' &&
    (record.methodologyId === null ||
      typeof record.methodologyId === 'number') &&
    typeof record.startDate === 'string' &&
    typeof record.endDate === 'string' &&
    typeof record.welcomeMessage === 'string' &&
    typeof record.allowIndividualShare === 'boolean'
  )
}

export function readDraft(): NewSurveyDraft | null {
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isValidDraft(parsed)) {
      window.localStorage.removeItem(DRAFT_KEY)
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function writeDraft(draft: NewSurveyDraft): void {
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
  } catch {}
}

export function clearDraft(): void {
  try {
    window.localStorage.removeItem(DRAFT_KEY)
  } catch {}
}
