from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire_at = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire_at}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, session_id: int) -> str:
    expire_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "session_id": session_id, "exp": expire_at}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return dict(jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM]))
    except (ExpiredSignatureError, JWTError) as exc:
        raise AuthenticationError("Токен недействителен или истек") from exc


def create_csrf_token() -> str:
    return token_urlsafe(32)
