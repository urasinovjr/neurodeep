export type MethodologyMetaDto = {
  id: number
  name: string
  description: string | null
  category: string | null
  total_questions: number
}

export type SurveyPreviewDto = {
  status: string
  welcome_message: string | null
  methodology: MethodologyMetaDto
}

export type QuestionPublicDto = {
  id: number
  text: string
  order_index: number
}

export type SessionStartDto = {
  session_id: string
  status: string
  welcome_message: string | null
  methodology: MethodologyMetaDto
}

export type ConsentDto = {
  session_id: string
  status: string
  next_question_index: number
  next_question: QuestionPublicDto
}

export type SessionStateInfoDto = {
  session_id: string
  status: string
  invite_token: string
  next_question_index: number
  total_questions: number
  progress_percent: number
  next_question: QuestionPublicDto | null
  completed_at: string | null
}

export type AnswerAcceptedDto = {
  status: string
  session_status: string
  next_question_index: number
}
