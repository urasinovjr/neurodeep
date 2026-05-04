# ruff: noqa: B008
from fastapi import APIRouter, Cookie, Depends, Header, Request, Response

from app.api.deps import get_auth_service, get_current_user, get_optional_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User
from app.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),  # noqa: B008
):
    user = await service.register(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        invite_token=payload.invite_token,
    )
    return user


@router.post("/verify-email", status_code=200)
async def verify_email(token: str, service: AuthService = Depends(get_auth_service)):  # noqa: B008
    await service.verify_email(token)
    return {"detail": "Email подтверждён"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),  # noqa: B008
):
    access, refresh, csrf = await service.login(
        email=payload.email,
        password=payload.password,
        ip=request.client.host,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    response.headers["X-CSRF-Token"] = csrf
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None),  # noqa: B008
    x_csrf_token: str | None = Header(None),  # noqa: B008
    service: AuthService = Depends(get_auth_service),  # noqa: B008
):
    access, new_refresh, csrf = await service.refresh(
        refresh_token=refresh_token or "",
        csrf_from_header=x_csrf_token or "",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    response.headers["X-CSRF-Token"] = csrf
    return TokenResponse(access_token=access)


@router.post("/logout", status_code=204)
@limiter.limit("30/minute")
async def logout(
    request: Request,
    current: User = Depends(get_current_user),  # noqa: B008
    service: AuthService = Depends(get_auth_service),  # noqa: B008
    refresh_token: str | None = Cookie(None),  # noqa: B008
):
    if refresh_token:
        from app.core.exceptions import AuthenticationError
        from app.core.security import decode_token
        try:
            claims = decode_token(refresh_token)
            session_id = int(claims.get("session_id", 0))
            if session_id:
                await service.logout(session_id)
        except AuthenticationError:
            pass


@router.get("/me", response_model=UserResponse)
@limiter.limit("100/minute")
async def me(
    request: Request,
    current: User = Depends(get_current_user),  # noqa: B008
):
    return current


@router.post("/password-reset-request", status_code=204)
@limiter.limit("3/minute")
async def password_reset_request(
    request: Request,
    payload: PasswordResetRequest,
    service: AuthService = Depends(get_auth_service),  # noqa: B008
):
    await service.password_reset_request(payload.email)


@router.post("/change-password", status_code=204)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    service: AuthService = Depends(get_auth_service),  # noqa: B008
    current: User | None = Depends(get_optional_current_user),  # noqa: B008
):
    await service.change_password(
        user_id=current.id if current else None,
        old_password=payload.old_password,
        reset_token=payload.reset_token,
        new_password=payload.new_password,
    )
