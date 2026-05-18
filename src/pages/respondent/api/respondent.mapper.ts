import type {
  MethodologyMetaDto,
  QuestionPublicDto,
  SessionStateInfoDto,
  SurveyPreviewDto,
} from './respondent.dto'

export type MethodologyMeta = {
  id: number
  name: string
  description: string | null
  category: string | null
  totalQuestions: number
}

export type SurveyPreview = {
  status: string
  welcomeMessage: string | null
  methodology: MethodologyMeta
}

export function mapMethodologyMeta(dto: MethodologyMetaDto): MethodologyMeta {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description,
    category: dto.category,
    totalQuestions: dto.total_questions,
  }
}

export function mapSurveyPreview(dto: SurveyPreviewDto): SurveyPreview {
  return {
    status: dto.status,
    welcomeMessage: dto.welcome_message,
    methodology: mapMethodologyMeta(dto.methodology),
  }
}

export type ChatQuestion = {
  id: number
  text: string
  orderIndex: number
}

export type SessionState = {
  sessionId: string
  status: string
  inviteToken: string
  nextQuestionIndex: number
  totalQuestions: number
  progressPercent: number
  nextQuestion: ChatQuestion | null
  completedAt: string | null
}

function mapQuestion(dto: QuestionPublicDto): ChatQuestion {
  return {
    id: dto.id,
    text: dto.text,
    orderIndex: dto.order_index,
  }
}

export function mapSessionState(dto: SessionStateInfoDto): SessionState {
  return {
    sessionId: dto.session_id,
    status: dto.status,
    inviteToken: dto.invite_token,
    nextQuestionIndex: dto.next_question_index,
    totalQuestions: dto.total_questions,
    progressPercent: dto.progress_percent,
    nextQuestion: dto.next_question ? mapQuestion(dto.next_question) : null,
    completedAt: dto.completed_at,
  }
}
