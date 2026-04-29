import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    ForbiddenError,
    GoneError,
    LockedError,
    NotFoundError,
    UnprocessableError,
)
from app.core.security import (
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import User, UserRole
from app.db.repositories import AuditLogRepository, SessionRepository, UserRepository

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.audit_repo = audit_repo

    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        invite_token: str | None = None,
    ) -> User:
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            raise AlreadyExistsError("Email уже используется")

        role = UserRole.PENDING
        if invite_token is not None:
            try:
                payload = jwt.decode(invite_token, settings.JWT_SECRET, algorithms=["HS256"])
                intended_role = payload.get("intended_role")
                if intended_role == "researcher":
                    role = UserRole.RESEARCHER
            except (ExpiredSignatureError, JWTError):
                role = UserRole.PENDING

        verification_token = secrets.token_urlsafe(32)
        user = await self.user_repo.create(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            email_verification_token=verification_token,
        )

        await self.audit_repo.log(action="auth.register", user_id=user.id)
        logger.info(
            "Email verification link for %s: /api/auth/verify-email?token=%s",
            email,
            verification_token,
        )
        return user

    async def verify_email(self, token: str) -> User:
        user = await self.user_repo.get_by_verification_token(token)
        if user is None:
            raise NotFoundError("Токен подтверждения не найден")

        user.email_verified = True
        user.email_verification_token = None
        await self.user_repo.update(user, email_verified=True, email_verification_token=None)

        await self.audit_repo.log(action="auth.email_verified", user_id=user.id)
        return user

    async def login(
        self,
        email: str,
        password: str,
        ip: str | None = None,
        device_info: str | None = None,
    ) -> tuple[str, str, str]:
        user = await self.user_repo.get_by_email(email)
        if user is None:
            raise AuthenticationError("Неверный email или пароль")

        now = _utcnow()
        if user.locked_until is not None and _ensure_aware(user.locked_until) > now:
            raise LockedError("Аккаунт временно заблокирован")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)

            await self.user_repo.update(
                user,
                failed_login_attempts=user.failed_login_attempts,
                locked_until=user.locked_until,
            )
            await self.audit_repo.log(action="auth.login_failed", user_id=user.id, ip_address=ip)
            raise AuthenticationError("Неверный email или пароль")

        user.failed_login_attempts = 0
        user.locked_until = None
        await self.user_repo.update(user, failed_login_attempts=0, locked_until=None)

        csrf_token = create_csrf_token()
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session = await self.session_repo.create(
            user_id=user.id,
            refresh_token_hash="temp",
            csrf_token=csrf_token,
            device_info=device_info,
            ip_address=ip,
            expires_at=expires_at,
            is_active=True,
        )

        refresh_token = create_refresh_token(user.id, session.id)
        refresh_token_hash = _hash_refresh_token(refresh_token)
        await self.session_repo.update(session, refresh_token_hash=refresh_token_hash)

        await self.audit_repo.log(action="auth.login_success", user_id=user.id, ip_address=ip)
        access_token = create_access_token(user.id)
        return access_token, refresh_token, csrf_token

    async def refresh(self, refresh_token: str, csrf_from_header: str) -> tuple[str, str, str]:
        claims = decode_token(refresh_token)
        user_id = int(claims["sub"])
        session_id = int(claims["session_id"])
        _ = session_id

        refresh_token_hash = _hash_refresh_token(refresh_token)
        session = await self.session_repo.get_by_refresh_token_hash(refresh_token_hash)
        if session is None:
            raise GoneError("Сессия больше недоступна")

        if not session.is_active:
            raise GoneError("Сессия больше недоступна")

        now = _utcnow()
        if _ensure_aware(session.expires_at) < now:
            raise GoneError("Сессия больше недоступна")

        if csrf_from_header != session.csrf_token:
            raise ForbiddenError("CSRF проверка не пройдена")

        await self.session_repo.deactivate(session)

        csrf_token = create_csrf_token()
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_session = await self.session_repo.create(
            user_id=user_id,
            refresh_token_hash="temp",
            csrf_token=csrf_token,
            device_info=session.device_info,
            ip_address=session.ip_address,
            expires_at=expires_at,
            is_active=True,
        )

        new_refresh_token = create_refresh_token(user_id, new_session.id)
        new_refresh_token_hash = _hash_refresh_token(new_refresh_token)
        await self.session_repo.update(new_session, refresh_token_hash=new_refresh_token_hash)

        await self.audit_repo.log(action="auth.login_success", user_id=user_id)
        access_token = create_access_token(user_id)
        return access_token, new_refresh_token, csrf_token

    async def logout(self, session_id: int) -> None:
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Сессия не найдена")

        await self.session_repo.deactivate(session)
        await self.audit_repo.log(action="auth.logout", user_id=session.user_id)

    async def password_reset_request(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if user is None:
            return

        reset_token = secrets.token_urlsafe(32)
        await self.user_repo.update(user, password_reset_token=reset_token)

        await self.audit_repo.log(action="auth.password_reset_request", user_id=user.id)
        logger.info(
            "Password reset link for %s: /api/auth/change-password?token=%s",
            email,
            reset_token,
        )

    async def change_password(
        self,
        user_id: int | None = None,
        old_password: str | None = None,
        reset_token: str | None = None,
        new_password: str | None = None,
    ) -> None:
        if new_password is None:
            raise UnprocessableError("Новый пароль обязателен")

        user: User | None = None
        if reset_token is not None:
            user = await self.user_repo.get_by_reset_token(reset_token)
            if user is None:
                raise NotFoundError("Токен сброса не найден")

        if old_password is not None:
            if user_id is None or user is None or user.id != user_id:
                raise UnprocessableError("Неверные данные для смены пароля")
            if not verify_password(old_password, user.password_hash):
                raise AuthenticationError("Неверный пароль")

        if user is None:
            raise UnprocessableError("Неверные данные для смены пароля")

        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        await self.user_repo.update(user, password_hash=user.password_hash, password_reset_token=None)

        await self.session_repo.deactivate_all_by_user(user.id)
        await self.audit_repo.log(action="auth.password_change", user_id=user.id)

