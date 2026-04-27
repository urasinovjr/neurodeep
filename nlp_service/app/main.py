from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.config import settings


_model_state: dict[str, bool] = {"loaded": False}


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=settings.MAX_TEXT_LENGTH)
    scale_ids: list[int] = Field(..., min_length=1)
    methodology_id: int


class PredictResponse(BaseModel):
    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    themes: list[dict[str, Any]] = Field(default_factory=list)


app = FastAPI(title="PsychoGraph NLP Service")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_loaded": _model_state["loaded"],
        "model_name": settings.MODEL_NAME,
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    return PredictResponse()
