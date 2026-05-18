import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import (
    SurveyServiceDep,
    SurveySessionServiceDep,
    require_role,
)
from app.core.limiter import limiter
from app.db.models import User, UserRole
from app.schemas.survey_schemas import (
    AnswerAcceptedResponse,
    AnswerSubmitRequest,
    ConsentResponse,
    MethodologyMetaResponse,
    QuestionPublicResponse,
    ScaleScoreItem,
    SessionResultResponse,
    SessionStartResponse,
    SessionStateInfoResponse,
    SurveyCreateRequest,
    SurveyDetailResponse,
    SurveyListResponse,
    SurveyPreviewResponse,
    SurveyResponse,
    SurveyUpdateRequest,
)

router = APIRouter(prefix="/api/surveys", tags=["surveys"])

ResearcherDep = Annotated[
    User, Depends(require_role(UserRole.RESEARCHER, UserRole.ADMIN))
]


def _session_rate_key(request: Request) -> str:
    session_id = request.path_params.get("session_id", "")
    return f"session:{session_id}"


def _progress_percent(next_index: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(next_index * 100 / total)


@router.get("", response_model=SurveyListResponse)
@limiter.limit("100/minute")
async def list_surveys(
    request: Request,
    service: SurveyServiceDep,
    user: ResearcherDep,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SurveyListResponse:
    rows, total = await service.list_for_researcher(
        researcher_id=user.id, status=status, limit=limit, offset=offset
    )
    return SurveyListResponse(
        items=[SurveyResponse.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SurveyResponse, status_code=201)
@limiter.limit("30/minute")
async def create_survey(
    request: Request,
    data: SurveyCreateRequest,
    service: SurveyServiceDep,
    user: ResearcherDep,
) -> SurveyResponse:
    survey = await service.create(
        researcher_id=user.id,
        methodology_id=data.methodology_id,
        name=data.name,
        welcome_message=data.welcome_message,
        start_date=data.start_date,
        end_date=data.end_date,
        allow_individual_share=data.allow_individual_share,
    )
    return SurveyResponse.model_validate(survey)


@router.get("/{survey_id}", response_model=SurveyDetailResponse)
@limiter.limit("100/minute")
async def get_survey(
    request: Request,
    survey_id: int,
    service: SurveyServiceDep,
    user: ResearcherDep,
) -> SurveyDetailResponse:
    survey, stats = await service.get_with_stats(survey_id, user.id)
    base = SurveyResponse.model_validate(survey).model_dump()
    base["invited_count"] = stats["invited"]
    base["completed_count"] = stats["completed"]
    return SurveyDetailResponse.model_validate(base)


@router.patch("/{survey_id}", response_model=SurveyResponse)
@limiter.limit("30/minute")
async def update_survey(
    request: Request,
    survey_id: int,
    data: SurveyUpdateRequest,
    service: SurveyServiceDep,
    user: ResearcherDep,
) -> SurveyResponse:
    survey = await service.update(survey_id, user.id, data)
    return SurveyResponse.model_validate(survey)


@router.post("/{survey_id}/archive", response_model=SurveyResponse)
@limiter.limit("30/minute")
async def archive_survey(
    request: Request,
    survey_id: int,
    service: SurveyServiceDep,
    user: ResearcherDep,
) -> SurveyResponse:
    survey = await service.archive(survey_id, user.id)
    return SurveyResponse.model_validate(survey)


@router.get(
    "/by-token/{invite_token}",
    response_model=SurveyPreviewResponse,
)
@limiter.limit("100/minute")
async def survey_preview(
    request: Request,
    invite_token: str,
    service: SurveySessionServiceDep,
) -> SurveyPreviewResponse:
    survey, questions = await service.preview_by_token(invite_token)
    methodology = await service.methodology_repo.get_by_id(survey.methodology_id)
    return SurveyPreviewResponse(
        status=survey.status,
        welcome_message=survey.welcome_message,
        methodology=MethodologyMetaResponse(
            id=methodology.id,
            name=methodology.name,
            description=methodology.description,
            category=methodology.category,
            total_questions=len(questions),
        ),
    )


@router.post(
    "/by-token/{invite_token}/sessions",
    response_model=SessionStartResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def start_session(
    request: Request,
    invite_token: str,
    service: SurveySessionServiceDep,
) -> SessionStartResponse:
    session, survey, questions = await service.start_by_token(invite_token)
    methodology = await service.methodology_repo.get_by_id(survey.methodology_id)
    return SessionStartResponse(
        session_id=session.id,
        status=session.status,
        welcome_message=survey.welcome_message,
        methodology=MethodologyMetaResponse(
            id=methodology.id,
            name=methodology.name,
            description=methodology.description,
            category=methodology.category,
            total_questions=len(questions),
        ),
    )


@router.post(
    "/sessions/{session_id}/consent",
    response_model=ConsentResponse,
)
async def give_consent(
    request: Request,
    session_id: uuid.UUID,
    service: SurveySessionServiceDep,
) -> ConsentResponse:
    session, next_question = await service.give_consent(session_id)
    return ConsentResponse(
        session_id=session.id,
        status=session.status,
        next_question_index=session.next_question_index,
        next_question=QuestionPublicResponse.model_validate(next_question),
    )


@router.get(
    "/sessions/{session_id}/state",
    response_model=SessionStateInfoResponse,
)
async def session_state(
    request: Request,
    session_id: uuid.UUID,
    service: SurveySessionServiceDep,
) -> SessionStateInfoResponse:
    session, survey, questions = await service.get_state(session_id)
    total = len(questions)
    next_question: QuestionPublicResponse | None = None
    if session.status == "in_progress" and session.next_question_index < total:
        next_question = QuestionPublicResponse.model_validate(
            questions[session.next_question_index]
        )
    return SessionStateInfoResponse(
        session_id=session.id,
        status=session.status,
        invite_token=survey.invite_token,
        next_question_index=session.next_question_index,
        total_questions=total,
        progress_percent=_progress_percent(session.next_question_index, total),
        next_question=next_question,
        completed_at=session.completed_at,
    )


@router.post(
    "/sessions/{session_id}/answer",
    response_model=AnswerAcceptedResponse,
    status_code=202,
)
@limiter.limit("30/minute", key_func=_session_rate_key)
async def submit_answer(
    request: Request,
    session_id: uuid.UUID,
    payload: AnswerSubmitRequest,
    service: SurveySessionServiceDep,
) -> AnswerAcceptedResponse:
    session = await service.submit_answer(
        session_id=session_id,
        question_id=payload.question_id,
        text=payload.text,
    )
    return AnswerAcceptedResponse(
        status="processing",
        session_status=session.status,
        next_question_index=session.next_question_index,
    )


@router.get(
    "/sessions/{session_id}/result",
    response_model=SessionResultResponse,
)
async def session_result(
    request: Request,
    session_id: uuid.UUID,
    service: SurveySessionServiceDep,
) -> SessionResultResponse:
    session, scores = await service.get_result(session_id)
    pinaba_url: str | None = None
    if session.pinaba_image_key:
        pinaba_url = f"/p/{session.pinaba_image_key}"
    profile_text: str | None = None
    if session.profile_json and isinstance(session.profile_json, dict):
        text_value = session.profile_json.get("text")
        if isinstance(text_value, str):
            profile_text = text_value
    return SessionResultResponse(
        session_id=session.id,
        status=session.status,
        completed_at=session.completed_at,
        scores=[ScaleScoreItem.model_validate(s) for s in scores],
        profile_text=profile_text,
        pinaba_url=pinaba_url,
    )
