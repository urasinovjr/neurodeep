import os
from collections.abc import AsyncIterator

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("MINIO_ROOT_USER", "test-minio-user")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "test-minio-password")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")

from typing import TYPE_CHECKING  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    eng = create_async_engine(settings.DATABASE_URL, future=True)
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        await eng.dispose()
        pytest.skip(f"Postgres недоступен: {exc}")

    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator["AsyncClient"]:
    from httpx import ASGITransport, AsyncClient

    from app.api.deps import get_current_user, get_db
    from app.db.models import User, UserRole, UserStatus
    from app.main import app

    async def override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_admin_user() -> User:
        return User(
            id=1,
            email="admin@test.local",
            password_hash="x",
            first_name="Admin",
            last_name="Test",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True,
            failed_login_attempts=0,
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_admin_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
