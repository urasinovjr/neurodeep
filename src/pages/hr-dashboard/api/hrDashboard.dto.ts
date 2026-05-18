export type SurveyListItemDto = {
  id: number
  researcher_id: number
  methodology_id: number
  name: string
  welcome_message: string | null
  start_date: string | null
  end_date: string | null
  allow_individual_share: boolean
  status: string
  invite_token: string
  created_at: string
  invited_count: number
  completed_count: number
}

export type SurveyListDto = {
  items: SurveyListItemDto[]
  total: number
  limit: number
  offset: number
}
