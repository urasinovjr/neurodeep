from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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
    theme_tags: Mapped[Any | None] = mapped_column(JSONB)

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
    theme_tags: Mapped[Any | None] = mapped_column(JSONB)
    order_universal: Mapped[int | None] = mapped_column(Integer)
    is_universal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
