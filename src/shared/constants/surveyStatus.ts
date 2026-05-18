import type { SurveyStatus } from '../types/survey'

export const SURVEY_STATUS_LABEL: Record<SurveyStatus, string> = {
  draft: 'Черновик',
  active: 'Активно',
  archived: 'В архиве',
  completed: 'Завершено',
}

export const SURVEY_STATUS_CLASS: Record<SurveyStatus, string> = {
  draft: 'survey-status-draft',
  active: 'survey-status-active',
  archived: 'survey-status-archived',
  completed: 'survey-status-completed',
}

export const SURVEY_STATUS_DEFAULT_CLASS = 'survey-status-default'

export function getSurveyStatusLabel(status: string): string {
  return SURVEY_STATUS_LABEL[status as SurveyStatus] ?? status
}

export function getSurveyStatusClass(status: string): string {
  return SURVEY_STATUS_CLASS[status as SurveyStatus] ?? SURVEY_STATUS_DEFAULT_CLASS
}
