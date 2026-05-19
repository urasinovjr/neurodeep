import { apiClient } from '../../../shared/api/client'
import type {
  SurveyCreateRequestDto,
  SurveyCreatedDto,
} from './newSurvey.dto'

export async function createSurvey(
  payload: SurveyCreateRequestDto,
): Promise<SurveyCreatedDto> {
  return apiClient.post<SurveyCreatedDto>('/surveys', payload)
}
