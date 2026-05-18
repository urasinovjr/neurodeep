import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy import delete as sql_delete
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app.db.models import (
    AuditLog,
    Invitation,
    Methodology,
    PinabaArtifact,
    Question,
    QuestionScale,
    Scale,
    ScaleScore,
    Session,
    Survey,
    SurveySession,
    User,
    UserProfile,
    UserRole,
    UserStatus,
)
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


class MethodologyRepository(BaseRepository[Methodology]):
    model = Methodology

    async def get_published(self) -> list[Methodology]:
        result = await self.session.execute(
            select(Methodology).where(Methodology.status == "published").order_by(Methodology.id)
        )
        return list(result.scalars())

    async def get_drafts_by_author(self, author_id: int) -> list[Methodology]:
        result = await self.session.execute(
            select(Methodology)
            .where(Methodology.status == "draft", Methodology.author_id == author_id)
            .order_by(Methodology.id)
        )
        return list(result.scalars())

    async def get_by_id_with_scales_and_questions(
        self, methodology_id: int
    ) -> Methodology | None:
        result = await self.session.execute(
            select(Methodology)
            .where(Methodology.id == methodology_id)
            .options(
                selectinload(Methodology.scales),
                selectinload(Methodology.questions),
            )
        )
        return result.scalar_one_or_none()

    async def list_published_with_scales(self) -> list[Methodology]:
        result = await self.session.execute(
            select(Methodology)
            .where(Methodology.status == "published")
            .options(selectinload(Methodology.scales))
            .order_by(Methodology.id)
        )
        return list(result.scalars())

    async def list_paginated(
        self,
        status: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Methodology]:
        stmt = select(Methodology)
        if status:
            stmt = stmt.where(Methodology.status == status)
        if search:
            stmt = stmt.where(Methodology.name.ilike(f"%{search}%"))
        stmt = stmt.order_by(Methodology.id).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars())


class ScaleRepository(BaseRepository[Scale]):
    model = Scale

    async def get_by_methodology(self, methodology_id: int) -> list[Scale]:
        result = await self.session.execute(
            select(Scale)
            .where(Scale.methodology_id == methodology_id)
            .order_by(Scale.order_index)
        )
        return list(result.scalars())

    async def get_by_ids(self, ids: list[int]) -> list[Scale]:
        if not ids:
            return []
        result = await self.session.execute(
            select(Scale).where(Scale.id.in_(ids))
        )
        return list(result.scalars().all())

    async def bulk_create(self, scales: list[Scale]) -> list[Scale]:
        self.session.add_all(scales)
        await self.session.flush()
        return scales


class QuestionRepository(BaseRepository[Question]):
    model = Question

    async def get_by_methodology(self, methodology_id: int) -> list[Question]:
        result = await self.session.execute(
            select(Question)
            .where(Question.methodology_id == methodology_id)
            .order_by(Question.order_index)
        )
        return list(result.scalars())

    async def get_by_theme_tags(
        self, methodology_id: int, tags: list[str]
    ) -> list[Question]:
        result = await self.session.execute(
            select(Question)
            .where(
                Question.methodology_id == methodology_id,
                Question.theme_tags.op("?|")(array(tags)),
            )
            .order_by(Question.order_index)
        )
        return list(result.scalars())


class QuestionScaleRepository(BaseRepository[QuestionScale]):
    model = QuestionScale

    async def get_weights_for_question(self, question_id: int) -> list[QuestionScale]:
        result = await self.session.execute(
            select(QuestionScale).where(QuestionScale.question_id == question_id)
        )
        return list(result.scalars())

    async def set_weights(
        self, question_id: int, weights: dict[int, Decimal]
    ) -> list[QuestionScale]:
        await self.session.execute(
            sql_delete(QuestionScale).where(QuestionScale.question_id == question_id)
        )
        new_links = [
            QuestionScale(question_id=question_id, scale_id=scale_id, weight=weight)
            for scale_id, weight in weights.items()
        ]
        self.session.add_all(new_links)
        await self.session.flush()
        return new_links


class SurveyRepository(BaseRepository[Survey]):
    model = Survey

    async def get_by_invite_token(self, token: str) -> Survey | None:
        result = await self.session.execute(
            select(Survey).where(Survey.invite_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_researcher(
        self,
        researcher_id: int,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Survey], int]:
        filters = [Survey.researcher_id == researcher_id]
        if status is not None:
            filters.append(Survey.status == status)
        base = select(Survey).where(*filters)
        count_query = select(func.count()).select_from(Survey).where(*filters)
        result = await self.session.execute(
            base.order_by(Survey.id.desc()).limit(limit).offset(offset)
        )
        total = await self.session.scalar(count_query)
        return list(result.scalars().all()), int(total or 0)

    async def get_active(self) -> list[Survey]:
        result = await self.session.execute(
            select(Survey).where(Survey.status == "active").order_by(Survey.id)
        )
        return list(result.scalars().all())


class InvitationRepository(BaseRepository[Invitation]):
    model = Invitation

    async def get_by_token(self, token: uuid.UUID) -> Invitation | None:
        result = await self.session.execute(
            select(Invitation).where(Invitation.token == token)
        )
        return result.scalar_one_or_none()

    async def count_completed(self, survey_id: int) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(Invitation)
            .where(Invitation.survey_id == survey_id, Invitation.used_at.is_not(None))
        )
        return int(total or 0)


class SurveySessionRepository(BaseRepository[SurveySession]):
    model = SurveySession

    async def get_by_id(self, obj_id: uuid.UUID) -> SurveySession | None:  # type: ignore[override]
        return await self.session.get(SurveySession, obj_id)

    async def get_by_invite_and_anon(
        self, invitation_id: int, respondent_anon_id: uuid.UUID
    ) -> SurveySession | None:
        result = await self.session.execute(
            select(SurveySession).where(
                SurveySession.invitation_id == invitation_id,
                SurveySession.respondent_anon_id == respondent_anon_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_completed_for_survey(self, survey_id: int) -> list[SurveySession]:
        result = await self.session.execute(
            select(SurveySession)
            .where(
                SurveySession.survey_id == survey_id,
                SurveySession.status == "completed",
            )
            .order_by(SurveySession.completed_at.desc())
        )
        return list(result.scalars().all())


class ScaleScoreRepository(BaseRepository[ScaleScore]):
    model = ScaleScore

    async def get_by_session(self, session_id: uuid.UUID) -> list[ScaleScore]:
        result = await self.session.execute(
            select(ScaleScore)
            .where(ScaleScore.session_id == session_id)
            .order_by(ScaleScore.scale_id)
        )
        return list(result.scalars().all())

    async def bulk_create(self, scores: list[ScaleScore]) -> list[ScaleScore]:
        self.session.add_all(scores)
        await self.session.flush()
        return scores

    async def aggregate_avg_for_survey(self, survey_id: int) -> dict[int, Decimal]:
        stmt = (
            select(ScaleScore.scale_id, func.avg(ScaleScore.value).label("avg_value"))
            .join(SurveySession, SurveySession.id == ScaleScore.session_id)
            .where(
                SurveySession.survey_id == survey_id,
                SurveySession.status == "completed",
            )
            .group_by(ScaleScore.scale_id)
        )
        result = await self.session.execute(stmt)
        return {scale_id: Decimal(str(avg_value)) for scale_id, avg_value in result.all()}

    async def distribution_low_mid_high(
        self, survey_id: int, scale_id: int
    ) -> dict[str, int]:
        bucket = case(
            (ScaleScore.value < Decimal("34"), "low"),
            (ScaleScore.value < Decimal("67"), "mid"),
            else_="high",
        ).label("bucket")
        stmt = (
            select(bucket, func.count())
            .select_from(ScaleScore)
            .join(SurveySession, SurveySession.id == ScaleScore.session_id)
            .where(
                SurveySession.survey_id == survey_id,
                SurveySession.status == "completed",
                ScaleScore.scale_id == scale_id,
            )
            .group_by(bucket)
        )
        result = await self.session.execute(stmt)
        counts = {"low": 0, "mid": 0, "high": 0}
        for tier, count in result.all():
            counts[str(tier)] = int(count)
        return counts


class PinabaArtifactRepository(BaseRepository[PinabaArtifact]):
    model = PinabaArtifact

    async def get_by_uuid(self, public_uuid: uuid.UUID) -> PinabaArtifact | None:
        result = await self.session.execute(
            select(PinabaArtifact).where(PinabaArtifact.public_uuid == public_uuid)
        )
        return result.scalar_one_or_none()

    async def expire_old(self, now: datetime) -> int:
        result = await self.session.execute(
            sql_delete(PinabaArtifact).where(PinabaArtifact.expires_at < now)
        )
        await self.session.flush()
        return int(result.rowcount or 0)


class UserProfileRepository(BaseRepository[UserProfile]):
    model = UserProfile

    async def get_by_user(self, user_id: int) -> UserProfile | None:
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, user_id: int, encrypted_data: bytes, key_version: int = 1
    ) -> UserProfile:
        stmt = pg_insert(UserProfile).values(
            user_id=user_id,
            encrypted_data=encrypted_data,
            key_version=key_version,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserProfile.user_id],
            set_={
                "encrypted_data": stmt.excluded.encrypted_data,
                "key_version": stmt.excluded.key_version,
                "updated_at": func.now(),
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()
        result = await self.session.execute(
            select(UserProfile)
            .where(UserProfile.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        existing = result.scalar_one()
        return existing
