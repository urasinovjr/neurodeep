export type SurveyCreateRequestDto = {
  methodology_id: number
  name: string
  welcome_message: string | null
  start_date: string | null
  end_date: string | null
  allow_individual_share: boolean
}

export type SurveyCreatedDto = {
  id: number
  invite_token: string
  status: string
  methodology_id: number
  name: string
}
