from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ActorIdDep, IsAdminDep, MethodologyServiceDep
from app.schemas.methodology_schemas import (
    MethodologyCreateRequest,
    MethodologyResponse,
    MethodologyUpdateRequest,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionScaleSetRequest,
    ScaleCreateRequest,
    ScaleResponse,
)

router = APIRouter(prefix="/api/admin/methodologies", tags=["admin-methodologies"])


@router.get("", response_model=list[MethodologyResponse])
async def list_methodologies(
    service: MethodologyServiceDep,
    status: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MethodologyResponse]:
    rows = await service.methodology_repo.list_paginated(status, search, limit, offset)
    return [MethodologyResponse.model_validate(row) for row in rows]


@router.post("", response_model=MethodologyResponse, status_code=201)
async def create_methodology(
    data: MethodologyCreateRequest,
    actor_id: ActorIdDep,
    service: MethodologyServiceDep,
) -> MethodologyResponse:
    methodology = await service.create(actor_id, data)
    return MethodologyResponse.model_validate(methodology)


@router.patch("/{methodology_id}", response_model=MethodologyResponse)
async def update_methodology(
    methodology_id: int,
    data: MethodologyUpdateRequest,
    actor_id: ActorIdDep,
    is_admin: IsAdminDep,
    service: MethodologyServiceDep,
) -> MethodologyResponse:
    methodology = await service.update(methodology_id, data, actor_id, is_admin)
    return MethodologyResponse.model_validate(methodology)


@router.post(
    "/{methodology_id}/scales",
    response_model=ScaleResponse,
    status_code=201,
)
async def add_scale(
    methodology_id: int,
    data: ScaleCreateRequest,
    actor_id: ActorIdDep,
    is_admin: IsAdminDep,
    service: MethodologyServiceDep,
) -> ScaleResponse:
    scale = await service.add_scale(methodology_id, data, actor_id, is_admin)
    return ScaleResponse.model_validate(scale)


@router.post(
    "/{methodology_id}/questions",
    response_model=QuestionResponse,
    status_code=201,
)
async def add_question(
    methodology_id: int,
    data: QuestionCreateRequest,
    actor_id: ActorIdDep,
    is_admin: IsAdminDep,
    service: MethodologyServiceDep,
) -> QuestionResponse:
    weights = (
        QuestionScaleSetRequest(weights=data.scale_weights)
        if data.scale_weights
        else None
    )
    question = await service.add_question(
        methodology_id, data, weights, actor_id, is_admin
    )
    return QuestionResponse.model_validate(question)


@router.post("/{methodology_id}/publish", response_model=MethodologyResponse)
async def publish_methodology(
    methodology_id: int,
    actor_id: ActorIdDep,
    is_admin: IsAdminDep,
    service: MethodologyServiceDep,
) -> MethodologyResponse:
    methodology = await service.publish(methodology_id, actor_id, is_admin)
    return MethodologyResponse.model_validate(methodology)


@router.post("/{methodology_id}/archive", response_model=MethodologyResponse)
async def archive_methodology(
    methodology_id: int,
    actor_id: ActorIdDep,
    is_admin: IsAdminDep,
    service: MethodologyServiceDep,
) -> MethodologyResponse:
    methodology = await service.archive(methodology_id, actor_id, is_admin)
    return MethodologyResponse.model_validate(methodology)
