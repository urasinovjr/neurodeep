import re

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_-+=[]{};:,.<>/?|`"
PASSWORD_REGEX = re.compile(f"[{re.escape(PASSWORD_SPECIAL_CHARS)}]")


def _validate_password(v: str) -> str:
    if len(v) < 8 or len(v) > 128:
        raise ValueError("Пароль должен быть от 8 до 128 символов")
    if not re.search(r"[A-ZА-ЯЁ]", v):
        raise ValueError("Пароль должен содержать минимум одну заглавную букву")
    if not re.search(r"\d", v):
        raise ValueError("Пароль должен содержать минимум одну цифру")
    if not PASSWORD_REGEX.search(v):
        raise ValueError("Пароль должен содержать минимум один спецсимвол")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    invite_token: str | None = None

    @field_validator("password")
    @classmethod
    def password_must_match(cls, v: str) -> str:
        return _validate_password(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    csrf_token: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    status: str
    email_verified: bool

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    old_password: str | None = None
    reset_token: str | None = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_must_match(cls, v: str) -> str:
        return _validate_password(v)


class EmailChangeRequest(BaseModel):
    new_email: EmailStr

