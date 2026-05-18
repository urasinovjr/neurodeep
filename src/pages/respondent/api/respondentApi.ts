import { apiClient } from '../../../shared/api/client'
import type {
  AnswerAcceptedDto,
  ConsentDto,
  SessionResultDto,
  SessionStartDto,
  SessionStateInfoDto,
  SurveyPreviewDto,
} from './respondent.dto'
import {
  mapSessionResult,
  mapSessionState,
  mapSurveyPreview,
  type SessionResult,
  type SessionState,
  type SurveyPreview,
} from './respondent.mapper'

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '/api'

export async function fetchSurveyPreview(token: string): Promise<SurveyPreview> {
  const dto = await apiClient.get<SurveyPreviewDto>(
    `/surveys/by-token/${encodeURIComponent(token)}`,
  )
  return mapSurveyPreview(dto)
}

export async function startSession(token: string): Promise<SessionStartDto> {
  return apiClient.post<SessionStartDto>(
    `/surveys/by-token/${encodeURIComponent(token)}/sessions`,
  )
}

export async function giveConsent(sessionId: string): Promise<ConsentDto> {
  return apiClient.post<ConsentDto>(
    `/surveys/sessions/${encodeURIComponent(sessionId)}/consent`,
  )
}

export async function getSessionState(sessionId: string): Promise<SessionState> {
  const dto = await apiClient.get<SessionStateInfoDto>(
    `/surveys/sessions/${encodeURIComponent(sessionId)}/state`,
  )
  return mapSessionState(dto)
}

export async function submitAnswer(
  sessionId: string,
  questionId: number,
  text: string,
): Promise<AnswerAcceptedDto> {
  return apiClient.post<AnswerAcceptedDto>(
    `/surveys/sessions/${encodeURIComponent(sessionId)}/answer`,
    { question_id: questionId, text },
  )
}

export async function fetchSessionResult(sessionId: string): Promise<SessionResult> {
  const dto = await apiClient.get<SessionResultDto>(
    `/surveys/sessions/${encodeURIComponent(sessionId)}/result`,
  )
  return mapSessionResult(dto)
}

export function downloadPdfUrl(sessionId: string): string {
  return `${API_BASE}/surveys/sessions/${encodeURIComponent(sessionId)}/pdf`
}

export function downloadPinabaUrl(sessionId: string): string {
  return `${API_BASE}/surveys/sessions/${encodeURIComponent(sessionId)}/pinaba`
}
