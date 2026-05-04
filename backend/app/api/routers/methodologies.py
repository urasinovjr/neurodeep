from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import MethodologyServiceDep, require_role
from app.core.limiter import limiter
from app.db.models import User, UserRole
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

AdminUserDep = Annotated[User, Depends(require_role(UserRole.ADMIN))]


@router.get("", response_model=list[MethodologyResponse])
@limiter.limit("30/minute")
async def list_methodologies(
    request: Request,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
    status: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MethodologyResponse]:
    rows = await service.methodology_repo.list_paginated(status, search, limit, offset)
    return [MethodologyResponse.model_validate(row) for row in rows]


@router.post("", response_model=MethodologyResponse, status_code=201)
@limiter.limit("30/minute")
async def create_methodology(
    request: Request,
    data: MethodologyCreateRequest,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
) -> MethodologyResponse:
    methodology = await service.create(admin.id, data)
    return MethodologyResponse.model_validate(methodology)


@router.patch("/{methodology_id}", response_model=MethodologyResponse)
@limiter.limit("30/minute")
async def update_methodology(
    request: Request,
    methodology_id: int,
    data: MethodologyUpdateRequest,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
) -> MethodologyResponse:
    methodology = await service.update(methodology_id, data, admin.id, True)
    return MethodologyResponse.model_validate(methodology)


@router.post(
    "/{methodology_id}/scales",
    response_model=ScaleResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def add_scale(
    request: Request,
    methodology_id: int,
    data: ScaleCreateRequest,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
) -> ScaleResponse:
    scale = await service.add_scale(methodology_id, data, admin.id, True)
    return ScaleResponse.model_validate(scale)


@router.post(
    "/{methodology_id}/questions",
    response_model=QuestionResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def add_question(
    request: Request,
    methodology_id: int,
    data: QuestionCreateRequest,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
) -> QuestionResponse:
    weights = (
        QuestionScaleSetRequest(weights=data.scale_weights)
        if data.scale_weights
        else None
    )
    question = await service.add_question(
        methodology_id, data, weights, admin.id, True
    )
    return QuestionResponse.model_validate(question)


@router.post("/{methodology_id}/publish", response_model=MethodologyResponse)
@limiter.limit("30/minute")
async def publish_methodology(
    request: Request,
    methodology_id: int,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
) -> MethodologyResponse:
    methodology = await service.publish(methodology_id, admin.id, True)
    return MethodologyResponse.model_validate(methodology)


@router.post("/{methodology_id}/archive", response_model=MethodologyResponse)
@limiter.limit("30/minute")
async def archive_methodology(
    request: Request,
    methodology_id: int,
    service: MethodologyServiceDep,
    admin: AdminUserDep,
) -> MethodologyResponse:
    methodology = await service.archive(methodology_id, admin.id, True)
    return MethodologyResponse.model_validate(methodology)
