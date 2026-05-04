import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import torch
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer

from app.core.config import settings
from app.features import _ensure_sentiment_model, extract_features, unload_sentiment_model
from app.ridge import predict_score
from app.themes import _ensure_theme_embeddings, detect_themes, unload_theme_embeddings

logger = logging.getLogger("nlp_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


_started_at: float = time.monotonic()

_MODELS: dict[str, Any] = {"tokenizer": None, "model": None}
_model_state: dict[str, bool] = {
    "loaded": False,
    "sentiment_loaded": False,
    "themes_loaded": False,
}

_metrics: dict[str, float] = {
    "predict_requests_total": 0.0,
    "predict_errors_total": 0.0,
    "predict_duration_seconds_sum": 0.0,
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    started_at = time.perf_counter()
    logger.info("Loading model %s from cache %s", settings.MODEL_NAME, settings.MODEL_CACHE_DIR)
    tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME, cache_dir=settings.MODEL_CACHE_DIR)
    model = AutoModel.from_pretrained(settings.MODEL_NAME, cache_dir=settings.MODEL_CACHE_DIR)
    model.eval()

    with torch.no_grad():
        warmup_inputs = tokenizer("тест", return_tensors="pt", truncation=True, max_length=128)
        model(**warmup_inputs)

    _MODELS["tokenizer"] = tokenizer
    _MODELS["model"] = model
    _model_state["loaded"] = True

    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    logger.info("Model loaded in %.0fms", elapsed_ms)

    started_sent = time.perf_counter()
    try:
        _ensure_sentiment_model()
        extract_features("тест")
        _model_state["sentiment_loaded"] = True
        elapsed_sent = (time.perf_counter() - started_sent) * 1000.0
        logger.info("Sentiment model loaded in %.0fms", elapsed_sent)
    except Exception as exc:
        _model_state["sentiment_loaded"] = False
        logger.warning("Sentiment model not available: %s", exc)

    started_themes = time.perf_counter()
    try:
        _ensure_theme_embeddings()
        detect_themes("разогрев")
        _model_state["themes_loaded"] = True
        elapsed_themes = (time.perf_counter() - started_themes) * 1000.0
        logger.info("Theme embeddings loaded in %.0fms", elapsed_themes)
    except Exception as exc:
        _model_state["themes_loaded"] = False
        logger.warning("Theme embeddings not available: %s", exc)

    yield

    _MODELS["tokenizer"] = None
    _MODELS["model"] = None
    _model_state["loaded"] = False
    unload_sentiment_model()
    _model_state["sentiment_loaded"] = False
    unload_theme_embeddings()
    _model_state["themes_loaded"] = False


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=settings.MAX_TEXT_LENGTH)
    scale_ids: list[int] = Field(..., min_length=1)
    methodology_id: int


class PredictResponse(BaseModel):
    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    themes: list[dict[str, Any]] = Field(default_factory=list)


app = FastAPI(title="PsychoGraph NLP Service", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Некорректные данные запроса", "errors": exc.errors()},
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_loaded": _model_state["loaded"],
        "sentiment_loaded": _model_state["sentiment_loaded"],
        "themes_loaded": _model_state["themes_loaded"],
        "model_name": settings.MODEL_NAME,
        "uptime_seconds": round(time.monotonic() - _started_at, 2),
    }


@app.get("/metrics")
async def metrics() -> Response:
    uptime = time.monotonic() - _started_at
    lines = [
        "# HELP nlp_uptime_seconds Service uptime in seconds.",
        "# TYPE nlp_uptime_seconds gauge",
        f"nlp_uptime_seconds {uptime:.2f}",
        "# HELP nlp_model_loaded ruBERT model loaded (0 or 1).",
        "# TYPE nlp_model_loaded gauge",
        f"nlp_model_loaded {1 if _model_state['loaded'] else 0}",
        "# HELP nlp_sentiment_loaded Sentiment model loaded (0 or 1).",
        "# TYPE nlp_sentiment_loaded gauge",
        f"nlp_sentiment_loaded {1 if _model_state['sentiment_loaded'] else 0}",
        "# HELP nlp_themes_loaded Theme reference embeddings loaded (0 or 1).",
        "# TYPE nlp_themes_loaded gauge",
        f"nlp_themes_loaded {1 if _model_state['themes_loaded'] else 0}",
        "# HELP nlp_predict_requests_total Total /predict requests received.",
        "# TYPE nlp_predict_requests_total counter",
        f"nlp_predict_requests_total {int(_metrics['predict_requests_total'])}",
        "# HELP nlp_predict_errors_total /predict requests that failed with 5xx.",
        "# TYPE nlp_predict_errors_total counter",
        f"nlp_predict_errors_total {int(_metrics['predict_errors_total'])}",
        "# HELP nlp_predict_duration_seconds_sum Cumulative wall-clock time spent in /predict.",
        "# TYPE nlp_predict_duration_seconds_sum counter",
        f"nlp_predict_duration_seconds_sum {_metrics['predict_duration_seconds_sum']:.4f}",
    ]
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def _embed_cls(text: str) -> Any:
    tokenizer = _MODELS["tokenizer"]
    model = _MODELS["model"]
    if tokenizer is None or model is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[0, 0, :].cpu().numpy()


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    started = time.monotonic()
    _metrics["predict_requests_total"] += 1
    try:
        embedding = _embed_cls(request.text)
        scores: dict[str, dict[str, float]] = {
            str(sid): predict_score(sid, request.text, embedding) for sid in request.scale_ids
        }
        themes = detect_themes(request.text)
        return PredictResponse(scores=scores, themes=themes)
    except HTTPException:
        raise
    except Exception as exc:
        _metrics["predict_errors_total"] += 1
        logger.exception(
            "Predict failed: scales=%s methodology=%s error=%s",
            request.scale_ids,
            request.methodology_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Ошибка предсказания") from exc
    finally:
        _metrics["predict_duration_seconds_sum"] += time.monotonic() - started
