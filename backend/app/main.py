from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AppError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    GoneError,
    LockedError,
    NotFoundError,
    UnprocessableError,
)

app = FastAPI(title="PsychoGraph Backend")


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    app_error = cast(AppError, exc)
    return JSONResponse({"detail": app_error.message}, status_code=app_error.status_code)


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "nlp_service": settings.NLP_SERVICE_URL}


for error_cls in (
    NotFoundError,
    AlreadyExistsError,
    AuthenticationError,
    ForbiddenError,
    ConflictError,
    GoneError,
    UnprocessableError,
    LockedError,
):
    app.add_exception_handler(error_cls, app_error_handler)
