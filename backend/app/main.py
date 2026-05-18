from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routers import methodologies, methodologies_public, surveys
from app.api.routers.admin.invitations import router as invitations_router
from app.api.routers.auth import router as auth_router
from app.core.config import settings
from app.core.csrf_middleware import CSRFDoubleSubmitMiddleware
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
from app.core.limiter import limiter

app = FastAPI(title="PsychoGraph Backend")
app.state.limiter = limiter
app.add_middleware(CSRFDoubleSubmitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(invitations_router, prefix="/api/admin", tags=["admin"])
app.include_router(methodologies.router)
app.include_router(methodologies_public.router)
app.include_router(surveys.router)
