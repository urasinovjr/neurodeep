from collections.abc import AsyncIterator, Callable

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_token
from app.db.models import User, UserRole, UserStatus
from app.db.repositories import AuditLogRepository, SessionRepository, UserRepository
from app.db.session import AsyncSessionLocal
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

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
    async def dependency(current: User = Depends(get_current_user)) -> User:  # noqa: B008
        if current.role not in roles:
            raise ForbiddenError("Недостаточно прав")
        return current

    return dependency

async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:  # noqa: B008
    return AuthService(
        user_repo=UserRepository(db),
        session_repo=SessionRepository(db),
        audit_service=AuditService(AuditLogRepository(db)),
    )
