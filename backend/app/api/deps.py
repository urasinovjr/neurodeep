from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import (
    MethodologyRepository,
    QuestionRepository,
    QuestionScaleRepository,
    ScaleRepository,
)
from app.db.session import AsyncSessionLocal
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
