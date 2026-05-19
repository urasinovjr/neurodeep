import type { SurveyDetailDto } from './surveyDetail.dto'

export type SurveyDetail = {
  id: number
  methodologyId: number
  name: string
  welcomeMessage: string | null
  startDate: string | null
  endDate: string | null
  allowIndividualShare: boolean
  status: string
  inviteToken: string
  createdAt: string
  invitedCount: number
  completedCount: number
  completionRate: number
}

export function mapSurveyDetail(dto: SurveyDetailDto): SurveyDetail {
  const rate =
    dto.invited_count > 0 ? dto.completed_count / dto.invited_count : 0
  return {
    id: dto.id,
    methodologyId: dto.methodology_id,
    name: dto.name,
    welcomeMessage: dto.welcome_message,
    startDate: dto.start_date,
    endDate: dto.end_date,
    allowIndividualShare: dto.allow_individual_share,
    status: dto.status,
    inviteToken: dto.invite_token,
    createdAt: dto.created_at,
    invitedCount: dto.invited_count,
    completedCount: dto.completed_count,
    completionRate: rate,
  }
}
