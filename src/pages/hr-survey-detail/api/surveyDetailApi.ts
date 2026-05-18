import { apiClient } from '../../../shared/api/client'
import type { SurveyDetailDto } from './surveyDetail.dto'
import { mapSurveyDetail, type SurveyDetail } from './surveyDetail.mapper'

export async function fetchSurveyDetail(
  surveyId: number,
): Promise<SurveyDetail> {
  const dto = await apiClient.get<SurveyDetailDto>(`/surveys/${surveyId}`)
  return mapSurveyDetail(dto)
}

export async function archiveSurvey(surveyId: number): Promise<SurveyDetail> {
  const dto = await apiClient.post<SurveyDetailDto>(
    `/surveys/${surveyId}/archive`,
  )
  return mapSurveyDetail(dto)
}
