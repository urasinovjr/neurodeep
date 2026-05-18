import logging
import secrets
from datetime import datetime

from sqlalchemy import func, select

from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.db.models import Invitation, Survey, SurveySession
from app.db.repositories import (
    InvitationRepository,
    MethodologyRepository,
    SurveyRepository,
    SurveySessionRepository,
)
from app.schemas.survey_schemas import SurveyUpdateRequest
from app.services.audit_service import AuditService

logger = logging.getLogger("survey_service")

_INVITE_TOKEN_BYTES = 24


class SurveyService:
    def __init__(
        self,
        survey_repo: SurveyRepository,
        invitation_repo: InvitationRepository,
        session_repo: SurveySessionRepository,
        methodology_repo: MethodologyRepository,
        audit_service: AuditService,
    ) -> None:
        self.survey_repo = survey_repo
        self.invitation_repo = invitation_repo
        self.session_repo = session_repo
        self.methodology_repo = methodology_repo
        self.audit_service = audit_service

    async def create(
        self,
        researcher_id: int,
        methodology_id: int,
        name: str,
        welcome_message: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        allow_individual_share: bool = False,
    ) -> Survey:
        methodology = await self.methodology_repo.get_by_id(methodology_id)
        if methodology is None:
            raise NotFoundError(f"Методика {methodology_id} не найдена")
        if methodology.status != "published":
            raise UnprocessableError(
                f"Опрос можно создать только по опубликованной методике (статус: {methodology.status})"
            )
        if start_date is not None and end_date is not None and start_date >= end_date:
            raise UnprocessableError("Дата начала должна быть раньше даты окончания")

        invite_token = secrets.token_urlsafe(_INVITE_TOKEN_BYTES)
        survey = await self.survey_repo.create(
            researcher_id=researcher_id,
            methodology_id=methodology_id,
            name=name,
            welcome_message=welcome_message,
            start_date=start_date,
            end_date=end_date,
            allow_individual_share=allow_individual_share,
            invite_token=invite_token,
            status="draft",
        )
        await self.audit_service.log(
            action="survey.created",
            user_id=researcher_id,
            entity_type="survey",
            entity_id=survey.id,
        )
        logger.info("survey.created id=%s researcher_id=%s", survey.id, researcher_id)
        return survey

    async def list_for_researcher(
        self,
        researcher_id: int,
        status: str | None = None,
        methodology_id: int | None = None,
        sort: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[Survey, int, int]], int]:
        return await self.survey_repo.get_by_researcher(
            researcher_id=researcher_id,
            status=status,
            methodology_id=methodology_id,
            sort=sort,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )

    async def get_with_stats(
        self, survey_id: int, researcher_id: int
    ) -> tuple[Survey, dict[str, int]]:
        survey = await self._get_owned_or_raise(survey_id, researcher_id)
        invited_count = await self.survey_repo.session.scalar(
            select(func.count())
            .select_from(Invitation)
            .where(Invitation.survey_id == survey_id)
        )
        completed_count = await self.survey_repo.session.scalar(
            select(func.count())
            .select_from(SurveySession)
            .where(
                SurveySession.survey_id == survey_id,
                SurveySession.status == "completed",
            )
        )
        return survey, {
            "invited": int(invited_count or 0),
            "completed": int(completed_count or 0),
        }

    async def get_by_id_for_researcher(
        self, survey_id: int, researcher_id: int
    ) -> Survey:
        return await self._get_owned_or_raise(survey_id, researcher_id)

    async def update(
        self,
        survey_id: int,
        researcher_id: int,
        data: SurveyUpdateRequest,
    ) -> Survey:
        survey = await self._get_owned_or_raise(survey_id, researcher_id)
        if survey.status not in ("draft", "active"):
            raise UnprocessableError(
                f"Опрос можно изменять только в статусе draft или active (сейчас {survey.status})"
            )
        updates = data.model_dump(exclude_unset=True, exclude_none=False)
        if not updates:
            return survey

        new_start = updates.get("start_date", survey.start_date)
        new_end = updates.get("end_date", survey.end_date)
        if new_start is not None and new_end is not None and new_start >= new_end:
            raise UnprocessableError("Дата начала должна быть раньше даты окончания")

        for field, value in updates.items():
            setattr(survey, field, value)
        await self.survey_repo.session.flush()
        await self.audit_service.log(
            action="survey.updated",
            user_id=researcher_id,
            entity_type="survey",
            entity_id=survey.id,
        )
        logger.info(
            "survey.updated id=%s fields=%s", survey.id, sorted(updates.keys())
        )
        return survey

    async def archive(self, survey_id: int, researcher_id: int) -> Survey:
        survey = await self._get_owned_or_raise(survey_id, researcher_id)
        if survey.status == "archived":
            return survey
        survey.status = "archived"
        await self.survey_repo.session.flush()
        await self.audit_service.log(
            action="survey.archived",
            user_id=researcher_id,
            entity_type="survey",
            entity_id=survey.id,
        )
        logger.info("survey.archived id=%s", survey.id)
        return survey

    async def remind_pending(self, survey_id: int, researcher_id: int) -> str:
        survey = await self._get_owned_or_raise(survey_id, researcher_id)
        from app.tasks.survey_tasks import send_survey_reminders

        async_result = send_survey_reminders.delay(survey.id)
        await self.audit_service.log(
            action="survey.invite_sent",
            user_id=researcher_id,
            entity_type="survey",
            entity_id=survey.id,
        )
        logger.info(
            "survey.remind_pending id=%s task_id=%s", survey.id, async_result.id
        )
        return str(async_result.id)

    async def _get_owned_or_raise(
        self, survey_id: int, researcher_id: int
    ) -> Survey:
        survey = await self.survey_repo.get_by_id(survey_id)
        if survey is None:
            raise NotFoundError(f"Опрос {survey_id} не найден")
        if survey.researcher_id != researcher_id:
            raise ForbiddenError("Опрос принадлежит другому исследователю")
        return survey
