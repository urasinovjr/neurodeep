from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify():
    password_hash = hash_password("Test123!")

    assert password_hash != "Test123!"
    assert verify_password("Test123!", password_hash) is True
    assert verify_password("Wrong123!", password_hash) is False


def test_create_access_token_and_decode():
    token = create_access_token(1)

    claims = decode_token(token)

    assert claims["sub"] == "1"
    assert "exp" in claims


def test_create_refresh_token_and_decode():
    token = create_refresh_token(2, 15)

    claims = decode_token(token)

    assert claims["sub"] == "2"
    assert claims["session_id"] == 15
    assert "exp" in claims


def test_decode_token_with_invalid_secret_raises_authentication_error():
    token = jwt.encode({"sub": "1"}, "wrong-secret", algorithm="HS256")

    with pytest.raises(AuthenticationError, match="Токен недействителен или истек"):
        decode_token(token)


def test_decode_token_with_expired_token_raises_authentication_error():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AuthenticationError, match="Токен недействителен или истек"):
        decode_token(token)


def test_create_csrf_token_returns_unique_long_strings():
    token_1 = create_csrf_token()
    token_2 = create_csrf_token()

    assert isinstance(token_1, str)
    assert isinstance(token_2, str)
    assert len(token_1) >= 32
    assert len(token_2) >= 32
    assert token_1 != token_2
