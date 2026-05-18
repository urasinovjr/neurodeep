from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

PROTECTED_PATHS: frozenset[str] = frozenset({"/api/auth/refresh"})
PROTECTED_METHODS: frozenset[str] = frozenset({"POST"})


class CSRFDoubleSubmitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in PROTECTED_METHODS and request.url.path in PROTECTED_PATHS:
            cookie_token = request.cookies.get("csrf_token")
            header_token = request.headers.get("X-CSRF-Token")
            if not cookie_token or not header_token or cookie_token != header_token:
                return JSONResponse(
                    {"detail": "CSRF проверка не пройдена"},
                    status_code=403,
                )
        return await call_next(request)
