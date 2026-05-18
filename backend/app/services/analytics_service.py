import logging
from typing import Any

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.repositories import (
    InvitationRepository,
    ScaleRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
)

logger = logging.getLogger("analytics_service")


MIN_SESSIONS_FOR_AGGREGATES = 3
MIN_SESSIONS_PER_DEPARTMENT = 3
INSUFFICIENT_NOTE = (
    "Недостаточно данных — нужно минимум "
    f"{MIN_SESSIONS_FOR_AGGREGATES} завершённые сессии."
)


class AnalyticsService:
    def __init__(
        self,
        survey_repo: SurveyRepository,
        invitation_repo: InvitationRepository,
        session_repo: SurveySessionRepository,
        scale_repo: ScaleRepository,
        scale_score_repo: ScaleScoreRepository,
    ) -> None:
        self.survey_repo = survey_repo
        self.invitation_repo = invitation_repo
        self.session_repo = session_repo
        self.scale_repo = scale_repo
        self.scale_score_repo = scale_score_repo

    async def get_survey_analytics(
        self, survey_id: int, researcher_id: int | None
    ) -> dict[str, Any]:
        survey = await self.survey_repo.get_by_id(survey_id)
        if survey is None:
            raise NotFoundError(f"Опрос {survey_id} не найден")
        if researcher_id is not None and survey.researcher_id != researcher_id:
            raise ForbiddenError("Опрос принадлежит другому исследователю")

        total_invited = await self._count_invited(survey_id)
        total_completed = await self._count_completed(survey_id)
        completion_rate = (
            total_completed / total_invited if total_invited > 0 else 0.0
        )

        base: dict[str, Any] = {
            "total_invited": total_invited,
            "total_completed": total_completed,
            "completion_rate": round(completion_rate, 4),
            "is_sufficient": total_completed >= MIN_SESSIONS_FOR_AGGREGATES,
            "insufficient_note": None,
            "scale_averages": None,
            "scale_distribution": None,
            "department_comparison": None,
        }
        if total_completed < MIN_SESSIONS_FOR_AGGREGATES:
            base["insufficient_note"] = INSUFFICIENT_NOTE
            return base

        scales = await self.scale_repo.get_by_methodology(survey.methodology_id)
        averages_raw = await self.scale_score_repo.aggregate_avg_for_survey(
            survey_id
        )
        scale_averages: dict[int, dict[str, Any]] = {}
        scale_distribution: dict[int, dict[str, int]] = {}
        for scale in scales:
            avg_value = averages_raw.get(scale.id)
            scale_averages[scale.id] = {
                "scale_name": scale.name,
                "average": round(float(avg_value), 2) if avg_value is not None else None,
            }
            scale_distribution[scale.id] = (
                await self.scale_score_repo.distribution_low_mid_high(
                    survey_id, scale.id
                )
            )

        dept_rows = await self.scale_score_repo.aggregate_by_department(
            survey_id, min_sessions=MIN_SESSIONS_PER_DEPARTMENT
        )
        if dept_rows:
            department_comparison = [
                {
                    "department": dept,
                    "respondents_count": count,
                    "scale_averages": {
                        scale_id: round(float(avg), 2)
                        for scale_id, avg in averages.items()
                    },
                }
                for dept, count, averages in dept_rows
            ]
        else:
            department_comparison = []

        base["scale_averages"] = scale_averages
        base["scale_distribution"] = scale_distribution
        base["department_comparison"] = department_comparison
        return base

    async def _count_invited(self, survey_id: int) -> int:
        return await self.invitation_repo.count_for_survey(survey_id)

    async def _count_completed(self, survey_id: int) -> int:
        return await self.session_repo.count_completed(survey_id)
