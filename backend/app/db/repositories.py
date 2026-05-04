from decimal import Decimal

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import selectinload

from app.db.models import Methodology, Question, QuestionScale, Scale
from app.db.repository import BaseRepository


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
