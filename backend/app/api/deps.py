from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_token
from app.db.models import User, UserRole, UserStatus
from app.db.repositories import (
    AuditLogRepository,
    MethodologyRepository,
    QuestionRepository,
    QuestionScaleRepository,
    ScaleRepository,
    SessionRepository,
    UserRepository,
)
from app.db.session import AsyncSessionLocal
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.methodology_service import MethodologyService


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


def get_actor_id() -> int:
    return 1


def get_is_admin() -> bool:
    return True


MethodologyServiceDep = Annotated[MethodologyService, Depends(get_methodology_service)]
ActorIdDep = Annotated[int, Depends(get_actor_id)]
IsAdminDep = Annotated[bool, Depends(get_is_admin)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
