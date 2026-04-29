from datetime import datetime

from sqlalchemy import func, or_, select

from app.db.models import AuditLog, Session, User, UserRole, UserStatus
from app.db.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email_verification_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> User | None:
        result = await self.session.execute(select(User).where(User.password_reset_token == token))
        return result.scalar_one_or_none()

    async def get_list(
        self,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        filters = []
        if role is not None:
            filters.append(User.role == role)
        if status is not None:
            filters.append(User.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(User.email).like(pattern),
                    func.lower(User.first_name).like(pattern),
                    func.lower(User.last_name).like(pattern),
                )
            )

        base_query = select(User)
        count_query = select(func.count()).select_from(User)
        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        result = await self.session.execute(
            base_query.order_by(User.id).limit(limit).offset(offset)
        )
        total = await self.session.scalar(count_query)
        return list(result.scalars().all()), int(total or 0)


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def get_by_refresh_token_hash(self, hash_: str) -> Session | None:
        result = await self.session.execute(
            select(Session).where(Session.refresh_token_hash == hash_)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> list[Session]:
        result = await self.session.execute(
            select(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
            .order_by(Session.id)
        )
        return list(result.scalars().all())

    async def deactivate(self, session: Session) -> None:
        session.is_active = False
        await self.session.flush()

    async def deactivate_all_by_user(self, user_id: int) -> None:
        sessions = await self.get_active_by_user(user_id)
        for session in sessions:
            session.is_active = False
        await self.session.flush()


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def log(
        self,
        action: str,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        return await self.create(
            action=action,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
        )

    async def get_paginated(
        self,
        action: str | None = None,
        user_id: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if action is not None:
            filters.append(AuditLog.action == action)
        if user_id is not None:
            filters.append(AuditLog.user_id == user_id)
        if from_date is not None:
            filters.append(AuditLog.created_at >= from_date)
        if to_date is not None:
            filters.append(AuditLog.created_at <= to_date)

        base_query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)
        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        result = await self.session.execute(
            base_query.order_by(AuditLog.id.desc()).limit(limit).offset(offset)
        )
        total = await self.session.scalar(count_query)
        return list(result.scalars().all()), int(total or 0)
