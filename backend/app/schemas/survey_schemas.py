import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class SurveyCreateRequest(BaseModel):
    methodology_id: int
    name: Annotated[str, Field(min_length=1, max_length=200)]
    welcome_message: Annotated[str | None, Field(default=None, max_length=10000)] = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    allow_individual_share: bool = False


class SurveyUpdateRequest(BaseModel):
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=200)] = None
    welcome_message: Annotated[str | None, Field(default=None, max_length=10000)] = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    allow_individual_share: bool | None = None


class SurveyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    researcher_id: int
    methodology_id: int
    name: str
    welcome_message: str | None
    start_date: datetime | None
    end_date: datetime | None
    allow_individual_share: bool
    status: str
    invite_token: str
    created_at: datetime


class SurveyListItem(SurveyResponse):
    invited_count: int
    completed_count: int


class SurveyListResponse(BaseModel):
    items: list[SurveyListItem]
    total: int
    limit: int
    offset: int


class SurveyDetailResponse(SurveyResponse):
    invited_count: int
    completed_count: int


class AnswerSubmit(BaseModel):
    session_id: uuid.UUID
    question_id: int
    text: Annotated[str, Field(min_length=1, max_length=4000)]


class SessionStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    survey_id: int
    status: str
    next_question_index: int
    started_at: datetime | None
    completed_at: datetime | None


class ScaleScoreItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scale_id: int
    value: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("100"))]
    confidence: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]


class ScaleScoreBreakdownItem(BaseModel):
    scale_id: int
    scale_name: str
    value: float
    level: str
    fragment: str


class WheelBalance(BaseModel):
    emotions: float
    thinking: float
    body: float
    relationships: float
    meaning: float


class SessionResultResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    completed_at: datetime | None
    scores: list[ScaleScoreItem]
    profile_text: str | None = None
    pinaba_url: str | None = None
    scale_scores: list[ScaleScoreBreakdownItem] = []
    text_interpretation: str | None = None
    recommendations: list[str] = []
    wheel_balance: WheelBalance | None = None


class ScaleAverageEntry(BaseModel):
    scale_name: str
    average: float | None


class DepartmentSummary(BaseModel):
    department: str
    respondents_count: int
    scale_averages: dict[int, float]


class AnalyticsResponse(BaseModel):
    total_invited: int
    total_completed: int
    completion_rate: float
    is_sufficient: bool
    insufficient_note: str | None = None
    scale_averages: dict[int, ScaleAverageEntry] | None = None
    scale_distribution: dict[int, dict[str, int]] | None = None
    department_comparison: list[DepartmentSummary] | None = None


class MethodologyMetaResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str | None = None
    total_questions: int


class QuestionPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    order_index: int


class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    welcome_message: str | None
    methodology: MethodologyMetaResponse


class SurveyPreviewResponse(BaseModel):
    status: str
    welcome_message: str | None
    methodology: MethodologyMetaResponse


class ConsentResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    next_question_index: int
    next_question: QuestionPublicResponse


class SessionStateInfoResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    invite_token: str
    next_question_index: int
    total_questions: int
    progress_percent: int
    next_question: QuestionPublicResponse | None
    completed_at: datetime | None


class AnswerSubmitRequest(BaseModel):
    question_id: int
    text: Annotated[str, Field(min_length=10, max_length=4000)]


class AnswerAcceptedResponse(BaseModel):
    status: str
    session_status: str
    next_question_index: int
