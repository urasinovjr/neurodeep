from collections.abc import AsyncIterator, Callable
from functools import lru_cache
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.models import User, UserRole, UserStatus
from app.db.repositories import (
    AuditLogRepository,
    InvitationRepository,
    MethodologyRepository,
    QuestionRepository,
    QuestionScaleRepository,
    ScaleRepository,
    ScaleScoreRepository,
    SessionRepository,
    SurveyRepository,
    SurveySessionRepository,
    UserRepository,
)
from app.db.session import AsyncSessionLocal
from app.services.analytics_service import AnalyticsService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.methodology_service import MethodologyService
from app.services.pdf_service import PdfService
from app.services.profile_service import ProfileService
from app.services.session_service import SurveySessionService
from app.services.survey_service import SurveyService


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Требуется авторизация")

    token = authorization[7:]
    claims = decode_token(token)
    user_id = int(claims["sub"])

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthenticationError("Пользователь не найден или заблокирован")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_optional_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User | None:
    if not authorization:
        return None

    try:
        return await get_current_user(authorization=authorization, db=db)
    except AuthenticationError:
        return None


def require_role(*roles: UserRole) -> Callable:
    async def dependency(current: CurrentUserDep) -> User:
        if current.role not in roles:
            raise ForbiddenError("Недостаточно прав")
        return current

    return dependency


async def get_auth_service(db: SessionDep) -> AuthService:
    return AuthService(
        user_repo=UserRepository(db),
        session_repo=SessionRepository(db),
        audit_service=AuditService(AuditLogRepository(db)),
    )


async def get_methodology_service(session: SessionDep) -> MethodologyService:
    return MethodologyService(
        methodology_repo=MethodologyRepository(session),
        scale_repo=ScaleRepository(session),
        question_repo=QuestionRepository(session),
        question_scale_repo=QuestionScaleRepository(session),
    )


MethodologyServiceDep = Annotated[MethodologyService, Depends(get_methodology_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_survey_service(session: SessionDep) -> SurveyService:
    return SurveyService(
        survey_repo=SurveyRepository(session),
        invitation_repo=InvitationRepository(session),
        session_repo=SurveySessionRepository(session),
        methodology_repo=MethodologyRepository(session),
        audit_service=AuditService(AuditLogRepository(session)),
    )


SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


async def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(
        session_repo=SurveySessionRepository(session),
        survey_repo=SurveyRepository(session),
        methodology_repo=MethodologyRepository(session),
        scale_repo=ScaleRepository(session),
        scale_score_repo=ScaleScoreRepository(session),
    )


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


async def get_session_service(
    session: SessionDep,
    redis_client: RedisDep,
    profile_service: ProfileServiceDep,
) -> SurveySessionService:
    return SurveySessionService(
        survey_repo=SurveyRepository(session),
        session_repo=SurveySessionRepository(session),
        question_repo=QuestionRepository(session),
        scale_repo=ScaleRepository(session),
        scale_score_repo=ScaleScoreRepository(session),
        methodology_repo=MethodologyRepository(session),
        redis_client=redis_client,
        audit_service=AuditService(AuditLogRepository(session)),
        profile_service=profile_service,
    )


SurveySessionServiceDep = Annotated[
    SurveySessionService, Depends(get_session_service)
]


async def get_analytics_service(session: SessionDep) -> AnalyticsService:
    return AnalyticsService(
        survey_repo=SurveyRepository(session),
        invitation_repo=InvitationRepository(session),
        session_repo=SurveySessionRepository(session),
        scale_repo=ScaleRepository(session),
        scale_score_repo=ScaleScoreRepository(session),
    )


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


async def get_audit_service(session: SessionDep) -> AuditService:
    return AuditService(AuditLogRepository(session))


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


@lru_cache(maxsize=1)
def _pdf_service_singleton() -> PdfService:
    return PdfService()


def get_pdf_service() -> PdfService:
    return _pdf_service_singleton()


PdfServiceDep = Annotated[PdfService, Depends(get_pdf_service)]
