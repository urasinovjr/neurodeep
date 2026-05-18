import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ThemeTagsType = JSONB().with_variant(JSON(), "sqlite")
ProfileJsonType = JSONB().with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    PENDING = "pending"
    RESPONDENT = "respondent"
    RESEARCHER = "researcher"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.PENDING,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SQLAlchemyEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(255), nullable=False)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="audit_logs")


class Methodology(Base):
    __tablename__ = "methodologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    author_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scales: Mapped[list["Scale"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="Scale.order_index",
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="Question.order_index",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="methodologies_status_check",
        ),
    )


class Scale(Base):
    __tablename__ = "scales"

    id: Mapped[int] = mapped_column(primary_key=True)
    methodology_id: Mapped[int] = mapped_column(
        ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    min_value: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_value: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="100"
    )
    interpretation_low: Mapped[str | None] = mapped_column(Text)
    interpretation_mid: Mapped[str | None] = mapped_column(Text)
    interpretation_high: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    methodology: Mapped["Methodology"] = relationship(back_populates="scales")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    methodology_id: Mapped[int] = mapped_column(
        ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    theme_tags: Mapped[Any | None] = mapped_column(ThemeTagsType)

    methodology: Mapped["Methodology"] = relationship(back_populates="questions")
    scale_links: Mapped[list["QuestionScale"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class QuestionScale(Base):
    __tablename__ = "question_scales"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    scale_id: Mapped[int] = mapped_column(
        ForeignKey("scales.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    question: Mapped["Question"] = relationship(back_populates="scale_links")
    scale: Mapped["Scale"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name="question_scales_weight_range",
        ),
    )


class AdaptiveQuestionBank(Base):
    __tablename__ = "adaptive_question_bank"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    theme_tags: Mapped[Any | None] = mapped_column(ThemeTagsType)
    order_universal: Mapped[int | None] = mapped_column(Integer)
    is_universal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    researcher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    methodology_id: Mapped[int] = mapped_column(
        ForeignKey("methodologies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    welcome_message: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allow_individual_share: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    invite_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invitations: Mapped[list["Invitation"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["SurveySession"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="surveys_status_check",
        ),
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[uuid.UUID] = mapped_column(
        Uuid(), unique=True, nullable=False, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(100))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminded_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    survey: Mapped["Survey"] = relationship(back_populates="invitations")
    sessions: Mapped[list["SurveySession"]] = relationship(back_populates="invitation")


class SurveySession(Base):
    __tablename__ = "survey_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), primary_key=True, default=uuid.uuid4
    )
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invitation_id: Mapped[int | None] = mapped_column(
        ForeignKey("invitations.id", ondelete="SET NULL")
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    respondent_anon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), nullable=False, default=uuid.uuid4
    )
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_question_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="consent_pending"
    )
    profile_json: Mapped[Any | None] = mapped_column(ProfileJsonType)
    pinaba_image_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    survey: Mapped["Survey"] = relationship(back_populates="sessions")
    invitation: Mapped["Invitation | None"] = relationship(back_populates="sessions")
    scale_scores: Mapped[list["ScaleScore"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    pinaba_artifacts: Mapped[list["PinabaArtifact"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('consent_pending', 'in_progress', 'completed', 'abandoned')",
            name="survey_sessions_status_check",
        ),
    )


class ScaleScore(Base):
    __tablename__ = "scale_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("survey_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scale_id: Mapped[int] = mapped_column(
        ForeignKey("scales.id", ondelete="RESTRICT"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["SurveySession"] = relationship(back_populates="scale_scores")
    scale: Mapped["Scale"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "value >= 0 AND value <= 100",
            name="scale_scores_value_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="scale_scores_confidence_range",
        ),
    )


class PinabaArtifact(Base):
    __tablename__ = "pinaba_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("survey_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    public_uuid: Mapped[uuid.UUID] = mapped_column(
        Uuid(), unique=True, nullable=False, default=uuid.uuid4
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["SurveySession"] = relationship(back_populates="pinaba_artifacts")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    encrypted_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
