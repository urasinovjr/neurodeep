
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import AlreadyExistsError, AuthenticationError, ForbiddenError, LockedError
from app.db.models import AuditLog, Base, UserRole
from app.db.repositories import AuditLogRepository, SessionRepository, UserRepository
from app.services.auth_service import AuthService


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.anyio
async def test_register_creates_user_in_pending_and_audit_record(db_session: AsyncSession):
    service = AuthService(
        user_repo=UserRepository(db_session),
        session_repo=SessionRepository(db_session),
        audit_repo=AuditLogRepository(db_session),
    )

    user = await service.register(
        email="user@example.com",
        password="Valid123!",
        first_name="Ivan",
        last_name="Ivanov",
        invite_token=None,
    )
    await db_session.commit()

    assert user.role == UserRole.PENDING

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "auth.register", AuditLog.user_id == user.id)
    )
    audit = result.scalar_one_or_none()
    assert audit is not None


@pytest.mark.anyio
async def test_register_with_existing_email_raises_already_exists(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)
    audit_repo = AuditLogRepository(db_session)
    service = AuthService(user_repo=user_repo, session_repo=session_repo, audit_repo=audit_repo)

    await service.register(
        email="dup@example.com",
        password="Valid123!",
        first_name="One",
        last_name="User",
        invite_token=None,
    )
    await db_session.commit()

    with pytest.raises(AlreadyExistsError):
        await service.register(
            email="dup@example.com",
            password="Valid123!",
            first_name="Two",
            last_name="User",
            invite_token=None,
        )


@pytest.mark.anyio
async def test_login_lockout_after_five_failed_attempts(db_session: AsyncSession):
    service = AuthService(
        user_repo=UserRepository(db_session),
        session_repo=SessionRepository(db_session),
        audit_repo=AuditLogRepository(db_session),
    )

    await service.register(
        email="lock@example.com",
        password="Valid123!",
        first_name="Lock",
        last_name="User",
        invite_token=None,
    )
    await db_session.commit()

    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await service.login(
                email="lock@example.com",
                password="Wrong123!",
                ip="127.0.0.1",
                device_info=None,
            )
        await db_session.commit()

    with pytest.raises(LockedError):
        await service.login(
            email="lock@example.com",
            password="Wrong123!",
            ip="127.0.0.1",
            device_info=None,
        )


@pytest.mark.anyio
async def test_refresh_with_wrong_csrf_raises_forbidden(db_session: AsyncSession):
    service = AuthService(
        user_repo=UserRepository(db_session),
        session_repo=SessionRepository(db_session),
        audit_repo=AuditLogRepository(db_session),
    )

    await service.register(
        email="refresh@example.com",
        password="Valid123!",
        first_name="Refresh",
        last_name="User",
        invite_token=None,
    )
    await db_session.commit()

    _, refresh_token, csrf = await service.login(
        email="refresh@example.com",
        password="Valid123!",
        ip="127.0.0.1",
        device_info=None,
    )
    await db_session.commit()

    with pytest.raises(ForbiddenError):
        await service.refresh(refresh_token=refresh_token, csrf_from_header="wrong-csrf")

