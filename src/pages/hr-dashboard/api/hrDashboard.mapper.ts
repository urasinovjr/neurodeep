import type {
  SurveyListDto,
  SurveyListItemDto,
} from './hrDashboard.dto'

export type SurveyListItem = {
  id: number
  name: string
  methodologyId: number
  welcomeMessage: string | null
  startDate: string | null
  endDate: string | null
  status: string
  inviteToken: string
  createdAt: string
  invitedCount: number
  completedCount: number
  completionRate: number
}

export type SurveyList = {
  items: SurveyListItem[]
  total: number
  limit: number
  offset: number
}

export function mapSurveyListItem(dto: SurveyListItemDto): SurveyListItem {
  const rate =
    dto.invited_count > 0 ? dto.completed_count / dto.invited_count : 0
  return {
    id: dto.id,
    name: dto.name,
    methodologyId: dto.methodology_id,
    welcomeMessage: dto.welcome_message,
    startDate: dto.start_date,
    endDate: dto.end_date,
    status: dto.status,
    inviteToken: dto.invite_token,
    createdAt: dto.created_at,
    invitedCount: dto.invited_count,
    completedCount: dto.completed_count,
    completionRate: rate,
  }
}

export function mapSurveyList(dto: SurveyListDto): SurveyList {
  return {
    items: dto.items.map(mapSurveyListItem),
    total: dto.total,
    limit: dto.limit,
    offset: dto.offset,
  }
}
