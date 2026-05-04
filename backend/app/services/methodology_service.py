import logging
from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.db.models import Methodology, Question, Scale
from app.db.repositories import (
    MethodologyRepository,
    QuestionRepository,
    QuestionScaleRepository,
    ScaleRepository,
)
from app.schemas.methodology_schemas import (
    MethodologyCreateRequest,
    MethodologyUpdateRequest,
    QuestionCreateRequest,
    QuestionScaleSetRequest,
    ScaleCreateRequest,
)

logger = logging.getLogger("methodology_service")

PUBLISH_MIN_SCALES = 3
PUBLISH_MIN_QUESTIONS = 5


class MethodologyService:
    def __init__(
        self,
        methodology_repo: MethodologyRepository,
        scale_repo: ScaleRepository,
        question_repo: QuestionRepository,
        question_scale_repo: QuestionScaleRepository,
    ) -> None:
        self.methodology_repo = methodology_repo
        self.scale_repo = scale_repo
        self.question_repo = question_repo
        self.question_scale_repo = question_scale_repo

    async def create(
        self, author_id: int | None, data: MethodologyCreateRequest
    ) -> Methodology:
        methodology = await self.methodology_repo.create(
            name=data.name,
            description=data.description,
            category=data.category,
            author_id=author_id,
        )
        logger.info(
            "methodology.created id=%s author_id=%s", methodology.id, author_id
        )
        return methodology

    async def update(
        self,
        methodology_id: int,
        data: MethodologyUpdateRequest,
        actor_id: int | None,
        is_admin: bool,
    ) -> Methodology:
        methodology = await self._get_draft_or_fail(methodology_id, actor_id, is_admin)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(methodology, field, value)
        await self.methodology_repo.session.flush()
        logger.info(
            "methodology.updated id=%s fields=%s",
            methodology.id,
            sorted(updates.keys()),
        )
        return methodology

    async def add_scale(
        self,
        methodology_id: int,
        data: ScaleCreateRequest,
        actor_id: int | None,
        is_admin: bool,
    ) -> Scale:
        methodology = await self._get_draft_or_fail(methodology_id, actor_id, is_admin)
        scale = Scale(
            methodology_id=methodology.id,
            name=data.name,
            description=data.description,
            interpretation_low=data.interpretation_low,
            interpretation_mid=data.interpretation_mid,
            interpretation_high=data.interpretation_high,
            min_value=data.min_value,
            max_value=data.max_value,
            order_index=data.order_index,
        )
        self.scale_repo.session.add(scale)
        await self.scale_repo.session.flush()
        logger.info(
            "scale.added scale_id=%s methodology_id=%s", scale.id, methodology.id
        )
        return scale

    async def add_question(
        self,
        methodology_id: int,
        data: QuestionCreateRequest,
        scale_weights: QuestionScaleSetRequest | None,
        actor_id: int | None,
        is_admin: bool,
    ) -> Question:
        methodology = await self._get_draft_or_fail(methodology_id, actor_id, is_admin)
        question = Question(
            methodology_id=methodology.id,
            text=data.text,
            order_index=data.order_index,
            theme_tags=data.theme_tags,
        )
        self.question_repo.session.add(question)
        await self.question_repo.session.flush()

        if scale_weights is not None:
            await self.question_scale_repo.set_weights(
                question.id,
                {item.scale_id: item.weight for item in scale_weights.weights},
            )
        logger.info(
            "question.added question_id=%s methodology_id=%s", question.id, methodology.id
        )
        return question

    async def publish(
        self, methodology_id: int, actor_id: int | None, is_admin: bool
    ) -> Methodology:
        methodology = await self._get_draft_or_fail(methodology_id, actor_id, is_admin)

        scales_count = len(await self.scale_repo.get_by_methodology(methodology.id))
        questions_count = len(await self.question_repo.get_by_methodology(methodology.id))

        if scales_count < PUBLISH_MIN_SCALES:
            raise UnprocessableError(
                f"Минимум {PUBLISH_MIN_SCALES} шкалы (сейчас {scales_count})"
            )
        if questions_count < PUBLISH_MIN_QUESTIONS:
            raise UnprocessableError(
                f"Минимум {PUBLISH_MIN_QUESTIONS} вопросов (сейчас {questions_count})"
            )

        methodology.status = "published"
        methodology.published_at = datetime.now(UTC)
        await self.methodology_repo.session.flush()
        logger.info("methodology.published id=%s", methodology.id)
        return methodology

    async def archive(
        self, methodology_id: int, actor_id: int | None, is_admin: bool
    ) -> Methodology:
        methodology = await self.methodology_repo.get_by_id(methodology_id)
        if methodology is None:
            raise NotFoundError(f"Методика {methodology_id} не найдена")
        if not is_admin and methodology.author_id != actor_id:
            raise ForbiddenError("Архивировать может только автор или администратор")

        active_surveys = await self._count_active_surveys(methodology.id)
        if active_surveys > 0:
            raise ConflictError(
                f"Нельзя архивировать методику с активными опросами (сейчас {active_surveys})"
            )

        methodology.status = "archived"
        await self.methodology_repo.session.flush()
        logger.info("methodology.archived id=%s", methodology.id)
        return methodology

    async def _get_draft_or_fail(
        self, methodology_id: int, actor_id: int | None, is_admin: bool
    ) -> Methodology:
        methodology = await self.methodology_repo.get_by_id(methodology_id)
        if methodology is None:
            raise NotFoundError(f"Методика {methodology_id} не найдена")
        if not is_admin and methodology.author_id != actor_id:
            raise ForbiddenError("Изменять методику может только её автор или администратор")
        if methodology.status != "draft":
            raise UnprocessableError(
                f"Методика не в статусе draft (текущий: {methodology.status})"
            )
        return methodology

    async def _count_active_surveys(self, methodology_id: int) -> int:
        return 0
