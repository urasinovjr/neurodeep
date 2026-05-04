from fastapi import APIRouter

from app.api.deps import MethodologyServiceDep
from app.core.exceptions import NotFoundError
from app.schemas.methodology_schemas import (
    MethodologyBriefResponse,
    MethodologyDetailResponse,
    QuestionResponse,
    ScaleResponse,
)

router = APIRouter(prefix="/api/methodologies", tags=["methodologies"])


@router.get("", response_model=list[MethodologyBriefResponse])
async def list_published_methodologies(
    service: MethodologyServiceDep,
) -> list[MethodologyBriefResponse]:
    methodologies = await service.methodology_repo.list_published_with_scales()
    return [
        MethodologyBriefResponse(
            id=m.id, name=m.name, category=m.category, scale_count=len(m.scales)
        )
        for m in methodologies
    ]


@router.get("/{methodology_id}", response_model=MethodologyDetailResponse)
async def get_methodology_detail(
    methodology_id: int,
    service: MethodologyServiceDep,
) -> MethodologyDetailResponse:
    methodology = await service.methodology_repo.get_by_id_with_scales_and_questions(
        methodology_id
    )
    if methodology is None or methodology.status != "published":
        raise NotFoundError(f"Опубликованная методика {methodology_id} не найдена")
    return MethodologyDetailResponse(
        id=methodology.id,
        name=methodology.name,
        description=methodology.description,
        category=methodology.category,
        status=methodology.status,
        author_id=methodology.author_id,
        created_at=methodology.created_at,
        published_at=methodology.published_at,
        scales=[ScaleResponse.model_validate(s) for s in methodology.scales],
        questions=[QuestionResponse.model_validate(q) for q in methodology.questions],
    )
