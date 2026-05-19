import type {
  MethodologyMetaDto,
  QuestionPublicDto,
  ScaleScoreBreakdownDto,
  SessionResultDto,
  SessionStateInfoDto,
  SurveyPreviewDto,
  WheelBalanceDto,
} from './respondent.dto'

export type ScaleLevel = 'low' | 'mid' | 'high'

function normalizeLevel(value: string): ScaleLevel {
  if (value === 'low' || value === 'mid' || value === 'high') return value
  return 'mid'
}

export type ScaleScoreBreakdown = {
  scaleId: number
  scaleName: string
  value: number
  level: ScaleLevel
  fragment: string
}

export type WheelBalance = WheelBalanceDto

export type SessionResult = {
  sessionId: string
  status: string
  completedAt: string | null
  profileText: string | null
  pinabaUrl: string | null
  scaleScores: ScaleScoreBreakdown[]
  textInterpretation: string | null
  recommendations: string[]
  wheelBalance: WheelBalance | null
}

function mapScaleScoreBreakdown(
  dto: ScaleScoreBreakdownDto,
): ScaleScoreBreakdown {
  return {
    scaleId: dto.scale_id,
    scaleName: dto.scale_name,
    value: dto.value,
    level: normalizeLevel(dto.level),
    fragment: dto.fragment,
  }
}

export function mapSessionResult(dto: SessionResultDto): SessionResult {
  return {
    sessionId: dto.session_id,
    status: dto.status,
    completedAt: dto.completed_at,
    profileText: dto.profile_text,
    pinabaUrl: dto.pinaba_url,
    scaleScores: dto.scale_scores.map(mapScaleScoreBreakdown),
    textInterpretation: dto.text_interpretation,
    recommendations: dto.recommendations,
    wheelBalance: dto.wheel_balance,
  }
}

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
