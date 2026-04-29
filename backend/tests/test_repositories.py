from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, UserRole, UserStatus
from app.db.repositories import AuditLogRepository, SessionRepository, UserRepository


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.anyio
async def test_base_repository_crud(db_session: AsyncSession):
    user_repo = UserRepository(db_session)

    user = await user_repo.create(
        email="base@example.com",
        password_hash="hash",
        first_name="Base",
        last_name="User",
    )
    await db_session.commit()

    fetched = await user_repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.email == "base@example.com"

    updated = await user_repo.update(fetched, first_name="Updated")
    await db_session.commit()
    assert updated.first_name == "Updated"

    all_users = await user_repo.get_all()
    assert len(all_users) == 1

    await user_repo.delete(updated)
    await db_session.commit()
    assert await user_repo.get_by_id(user.id) is None


@pytest.mark.anyio
async def test_user_repository_filters_and_token_lookups(db_session: AsyncSession):
    user_repo = UserRepository(db_session)

    first_user = await user_repo.create(
        email="anna@example.com",
        password_hash="hash1",
        first_name="Anna",
        last_name="Ivanova",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verification_token="verify-1",
        password_reset_token="reset-1",
    )
    await user_repo.create(
        email="boris@example.com",
        password_hash="hash2",
        first_name="Boris",
        last_name="Petrov",
        role=UserRole.RESEARCHER,
        status=UserStatus.BLOCKED,
    )
    await db_session.commit()

    by_email = await user_repo.get_by_email("anna@example.com")
    by_verification = await user_repo.get_by_verification_token("verify-1")
    by_reset = await user_repo.get_by_reset_token("reset-1")
    filtered, total = await user_repo.get_list(
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        search="anna",
    )

    assert by_email is not None
    assert by_email.id == first_user.id
    assert by_verification is not None
    assert by_verification.id == first_user.id
    assert by_reset is not None
    assert by_reset.id == first_user.id
    assert total == 1
    assert len(filtered) == 1
    assert filtered[0].id == first_user.id


@pytest.mark.anyio
async def test_session_repository_active_and_deactivate_methods(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    user = await user_repo.create(
        email="sessions@example.com",
        password_hash="hash",
        first_name="Session",
        last_name="Owner",
    )
    first_session = await session_repo.create(
        user_id=user.id,
        refresh_token_hash="refresh-1",
        csrf_token="csrf-1",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    second_session = await session_repo.create(
        user_id=user.id,
        refresh_token_hash="refresh-2",
        csrf_token="csrf-2",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    await db_session.commit()

    fetched = await session_repo.get_by_refresh_token_hash("refresh-1")
    active_sessions = await session_repo.get_active_by_user(user.id)

    assert fetched is not None
    assert fetched.id == first_session.id
    assert len(active_sessions) == 2

    await session_repo.deactivate(first_session)
    await db_session.commit()
    active_after_single = await session_repo.get_active_by_user(user.id)
    assert [session.id for session in active_after_single] == [second_session.id]

    await session_repo.deactivate_all_by_user(user.id)
    await db_session.commit()
    assert await session_repo.get_active_by_user(user.id) == []


@pytest.mark.anyio
async def test_audit_log_repository_log_and_paginate(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    audit_repo = AuditLogRepository(db_session)

    user = await user_repo.create(
        email="audit@example.com",
        password_hash="hash",
        first_name="Audit",
        last_name="User",
    )
    await audit_repo.log(
        action="auth.login_success",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        ip_address="127.0.0.1",
    )
    await audit_repo.log(action="auth.logout", user_id=user.id)
    await db_session.commit()

    items, total = await audit_repo.get_paginated(action="auth.login_success", user_id=user.id)

    assert total == 1
    assert len(items) == 1
    assert items[0].entity_type == "user"
    assert items[0].entity_id == user.id
    assert items[0].ip_address == "127.0.0.1"
