import { apiClient } from '../../../shared/api/client'
import type {
  MethodologyBriefDto,
  SurveyListDto,
} from './hrDashboard.dto'
import {
  mapMethodologyBrief,
  mapSurveyList,
  type MethodologyBrief,
  type SurveyList,
} from './hrDashboard.mapper'

export type SurveyListParams = {
  status?: string
  methodologyId?: number
  sort: 'created_at' | 'completion_rate'
  sortDir: 'asc' | 'desc'
  limit: number
  offset: number
}

function buildQuery(params: SurveyListParams): string {
  const usp = new URLSearchParams()
  if (params.status) usp.set('status', params.status)
  if (params.methodologyId !== undefined) {
    usp.set('methodology_id', String(params.methodologyId))
  }
  usp.set('sort', params.sort)
  usp.set('sort_dir', params.sortDir)
  usp.set('limit', String(params.limit))
  usp.set('offset', String(params.offset))
  return usp.toString()
}

export async function fetchSurveys(
  params: SurveyListParams,
): Promise<SurveyList> {
  const dto = await apiClient.get<SurveyListDto>(`/surveys?${buildQuery(params)}`)
  return mapSurveyList(dto)
}

export async function fetchMethodologies(): Promise<MethodologyBrief[]> {
  const list = await apiClient.get<MethodologyBriefDto[]>(`/methodologies`)
  return list.map(mapMethodologyBrief)
}
