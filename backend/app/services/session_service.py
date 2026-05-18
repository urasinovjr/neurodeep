import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis

from app.core.exceptions import (
    ConflictError,
    GoneError,
    NotFoundError,
    UnprocessableError,
)
from app.db.models import (
    Methodology,
    Question,
    ScaleScore,
    Survey,
    SurveySession,
)
from app.db.repositories import (
    MethodologyRepository,
    QuestionRepository,
    ScaleRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
)
from app.services.audit_service import AuditService
from app.services.profile_service import ProfileService
from app.tasks.process_answer import process_answer

logger = logging.getLogger("session_service")

ANSWER_TTL_SECONDS = 3600
MIN_ANSWER_TEXT_LENGTH = 10


class SurveySessionService:
    def __init__(
        self,
        survey_repo: SurveyRepository,
        session_repo: SurveySessionRepository,
        question_repo: QuestionRepository,
        scale_repo: ScaleRepository,
        scale_score_repo: ScaleScoreRepository,
        methodology_repo: MethodologyRepository,
        redis_client: aioredis.Redis,
        audit_service: AuditService,
        profile_service: ProfileService | None = None,
    ) -> None:
        self.survey_repo = survey_repo
        self.session_repo = session_repo
        self.question_repo = question_repo
        self.scale_repo = scale_repo
        self.scale_score_repo = scale_score_repo
        self.methodology_repo = methodology_repo
        self.redis = redis_client
        self.audit_service = audit_service
        self.profile_service = profile_service or ProfileService(
            session_repo=session_repo,
            survey_repo=survey_repo,
            methodology_repo=methodology_repo,
            scale_repo=scale_repo,
            scale_score_repo=scale_score_repo,
        )

    async def _resolve_active_survey(self, invite_token: str) -> Survey:
        survey = await self.survey_repo.get_by_invite_token(invite_token)
        if survey is None:
            raise NotFoundError("Опрос не найден")
        if survey.status not in ("draft", "active"):
            raise GoneError("Опрос закрыт")
        if (
            survey.end_date is not None
            and survey.end_date < datetime.now(UTC)
        ):
            raise GoneError("Срок прохождения опроса истёк")
        return survey

    async def _resolve_methodology(self, methodology_id: int) -> Methodology:
        methodology = await self.methodology_repo.get_by_id(methodology_id)
        if methodology is None:
            raise NotFoundError("Методика не найдена")
        return methodology

    async def preview_by_token(
        self, invite_token: str
    ) -> tuple[Survey, list[Question], Methodology]:
        survey = await self._resolve_active_survey(invite_token)
        questions = await self.question_repo.get_by_methodology(survey.methodology_id)
        if not questions:
            raise UnprocessableError("В методике опроса нет вопросов")
        methodology = await self._resolve_methodology(survey.methodology_id)
        return survey, questions, methodology

    async def start_by_token(
        self, invite_token: str
    ) -> tuple[SurveySession, Survey, list[Question], Methodology]:
        survey = await self._resolve_active_survey(invite_token)

        questions = await self.question_repo.get_by_methodology(survey.methodology_id)
        if not questions:
            raise UnprocessableError("В методике опроса нет вопросов")

        methodology = await self._resolve_methodology(survey.methodology_id)

        session = await self.session_repo.create(
            survey_id=survey.id,
            status="consent_pending",
            next_question_index=0,
        )
        logger.info(
            "session.created id=%s survey_id=%s", session.id, survey.id
        )
        return session, survey, questions, methodology

    async def give_consent(
        self, session_id: uuid.UUID
    ) -> tuple[SurveySession, Question]:
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Сессия не найдена")
        if session.status not in ("consent_pending", "in_progress"):
            raise ConflictError(
                f"Сессия в статусе '{session.status}', согласие невозможно"
            )

        survey = await self.survey_repo.get_by_id(session.survey_id)
        if survey is None:
            raise NotFoundError("Опрос не найден")
        questions = await self.question_repo.get_by_methodology(survey.methodology_id)
        if not questions:
            raise UnprocessableError("В методике опроса нет вопросов")

        if session.status == "consent_pending":
            now = datetime.now(UTC)
            session.consent_given_at = now
            session.started_at = now
            session.status = "in_progress"
            await self.session_repo.session.flush()
            await self.audit_service.log(
                action="session.consent_given",
                entity_type="survey_session",
                entity_id=survey.id,
            )
            logger.info(
                "session.consent_given id=%s survey_id=%s",
                session.id,
                survey.id,
            )

        index = min(session.next_question_index, len(questions) - 1)
        return session, questions[index]

    async def get_state(
        self, session_id: uuid.UUID
    ) -> tuple[SurveySession, Survey, list[Question]]:
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Сессия не найдена")
        survey = await self.survey_repo.get_by_id(session.survey_id)
        if survey is None:
            raise NotFoundError("Опрос не найден")
        questions = await self.question_repo.get_by_methodology(survey.methodology_id)
        return session, survey, questions

    async def submit_answer(
        self,
        session_id: uuid.UUID,
        question_id: int,
        text: str,
    ) -> SurveySession:
        if len(text) < MIN_ANSWER_TEXT_LENGTH:
            raise UnprocessableError(
                f"Ответ должен содержать минимум {MIN_ANSWER_TEXT_LENGTH} символов"
            )
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Сессия не найдена")
        if session.status != "in_progress":
            raise ConflictError(
                f"Сессия в статусе '{session.status}', ответ не принимается"
            )

        survey = await self.survey_repo.get_by_id(session.survey_id)
        if survey is None:
            raise NotFoundError("Опрос не найден")
        questions = await self.question_repo.get_by_methodology(survey.methodology_id)
        total = len(questions)
        if session.next_question_index >= total:
            raise ConflictError("Все вопросы уже отвечены")

        expected = questions[session.next_question_index]
        if expected.id != question_id:
            raise UnprocessableError(
                f"Ожидался вопрос {expected.id}, получен {question_id}"
            )

        redis_key = f"answer:{session_id}:{question_id}"
        await self.redis.setex(redis_key, ANSWER_TTL_SECONDS, text)
        process_answer.delay(str(session_id), question_id)

        session.next_question_index += 1
        if session.next_question_index >= total:
            session.status = "completed"
            session.completed_at = datetime.now(UTC)
            await self.audit_service.log(
                action="session.completed",
                entity_type="survey_session",
                entity_id=survey.id,
            )
            logger.info("session.completed id=%s", session.id)
        await self.session_repo.session.flush()
        return session

    async def get_result(
        self, session_id: uuid.UUID
    ) -> tuple[SurveySession, list[ScaleScore]]:
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise NotFoundError("Сессия не найдена")
        if session.status != "completed":
            raise UnprocessableError("Сессия не завершена")
        scores = await self.scale_score_repo.get_by_session(session_id)

        already_rendered = (
            isinstance(session.profile_json, dict)
            and bool(session.profile_json.get("text_interpretation"))
        )
        if scores and not already_rendered:
            await self._materialize_profile(session)

        return session, scores

    async def _materialize_profile(self, session: SurveySession) -> None:
        profile_json = await self.profile_service.build_profile_json(session.id)
        if profile_json is None:
            return
        session.profile_json = profile_json
        await self.session_repo.session.flush()
