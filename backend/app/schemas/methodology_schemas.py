from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class MethodologyCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str | None, Field(default=None, max_length=10000)] = None
    category: Annotated[str, Field(min_length=1, max_length=50)]


class MethodologyUpdateRequest(BaseModel):
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=200)] = None
    description: Annotated[str | None, Field(default=None, max_length=10000)] = None
    category: Annotated[str | None, Field(default=None, min_length=1, max_length=50)] = None


class MethodologyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str
    status: str
    author_id: int | None
    created_at: datetime
    published_at: datetime | None


class ScaleCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str | None, Field(default=None, max_length=10000)] = None
    interpretation_low: str | None = None
    interpretation_mid: str | None = None
    interpretation_high: str | None = None
    min_value: int = 0
    max_value: int = 100
    order_index: int = 0


class ScaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    methodology_id: int
    name: str
    description: str | None
    min_value: int
    max_value: int
    interpretation_low: str | None
    interpretation_mid: str | None
    interpretation_high: str | None
    order_index: int


class QuestionCreateRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=5000)]
    order_index: int = 0
    theme_tags: list[str] | None = None
    scale_weights: list["QuestionScaleItem"] | None = None


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    methodology_id: int
    text: str
    order_index: int
    theme_tags: list[str] | None


class QuestionScaleItem(BaseModel):
    scale_id: int
    weight: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]


class QuestionScaleSetRequest(BaseModel):
    weights: Annotated[list[QuestionScaleItem], Field(min_length=1)]


class MethodologyBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    scale_count: int


class MethodologyDetailResponse(MethodologyResponse):
    scales: list[ScaleResponse]
    questions: list[QuestionResponse]
