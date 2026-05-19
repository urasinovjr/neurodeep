import secrets
from decimal import Decimal

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
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
from app.db.repositories import (
    InvitationRepository,
    ScaleRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
)
from app.services.analytics_service import (
    INSUFFICIENT_NOTE,
    MIN_SESSIONS_FOR_AGGREGATES,
    AnalyticsService,
)


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(sql_delete(ScaleScore))
    await session.execute(sql_delete(PinabaArtifact))
    await session.execute(sql_delete(SurveySession))
    await session.execute(sql_delete(Invitation))
    await session.execute(sql_delete(Survey))
    await session.execute(sql_delete(UserProfile))
    await session.execute(sql_delete(QuestionScale))
    await session.execute(sql_delete(Question))
    await session.execute(sql_delete(Scale))
    await session.execute(sql_delete(Methodology))
    await session.execute(sql_delete(AuditLog))
    await session.execute(sql_delete(Session))
    await session.execute(sql_delete(User))
    researcher = User(
        id=1,
        email="r@test.local",
        password_hash="x",
        first_name="R",
        last_name="T",
        role=UserRole.RESEARCHER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        failed_login_attempts=0,
    )
    other = User(
        id=2,
        email="r2@test.local",
        password_hash="x",
        first_name="O",
        last_name="T",
        role=UserRole.RESEARCHER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        failed_login_attempts=0,
    )
    session.add_all([researcher, other])
    await session.commit()


async def _seed_methodology_with_scales(
    db_session: AsyncSession, scale_names: list[str]
) -> tuple[Methodology, list[Scale]]:
    methodology = Methodology(
        name="Analytics methodology", category="cbt", status="published"
    )
    db_session.add(methodology)
    await db_session.flush()
    scales: list[Scale] = []
    for idx, name in enumerate(scale_names):
        scale = Scale(
            methodology_id=methodology.id,
            name=name,
            order_index=idx,
        )
        db_session.add(scale)
        scales.append(scale)
    await db_session.flush()
    return methodology, scales


async def _seed_survey(
    db_session: AsyncSession, methodology: Methodology, researcher_id: int = 1
) -> Survey:
    survey = Survey(
        researcher_id=researcher_id,
        methodology_id=methodology.id,
        name="Analytics survey",
        invite_token=secrets.token_urlsafe(24),
        status="active",
    )
    db_session.add(survey)
    await db_session.flush()
    return survey


async def _add_invitation(
    db_session: AsyncSession,
    survey: Survey,
    department: str | None,
    used: bool = False,
) -> Invitation:
    inv = Invitation(
        survey_id=survey.id,
        department=department,
        email=f"{secrets.token_hex(4)}@example.com",
    )
    if used:
        from datetime import UTC, datetime

        inv.used_at = datetime.now(UTC)
    db_session.add(inv)
    await db_session.flush()
    return inv


async def _add_completed_session_with_scores(
    db_session: AsyncSession,
    survey: Survey,
    scales: list[Scale],
    scores: list[Decimal],
    invitation: Invitation | None = None,
) -> SurveySession:
    sess = SurveySession(
        survey_id=survey.id,
        status="completed",
        invitation_id=invitation.id if invitation else None,
    )
    db_session.add(sess)
    await db_session.flush()
    for scale, value in zip(scales, scores, strict=True):
        db_session.add(
            ScaleScore(
                session_id=sess.id,
                scale_id=scale.id,
                value=value,
                confidence=Decimal("0.8"),
            )
        )
    return sess


def _make_analytics_service(db_session: AsyncSession) -> AnalyticsService:
    return AnalyticsService(
        survey_repo=SurveyRepository(db_session),
        invitation_repo=InvitationRepository(db_session),
        session_repo=SurveySessionRepository(db_session),
        scale_repo=ScaleRepository(db_session),
        scale_score_repo=ScaleScoreRepository(db_session),
    )


async def test_unknown_survey_raises_not_found(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _make_analytics_service(db_session)
    with pytest.raises(NotFoundError):
        await service.get_survey_analytics(survey_id=999999, researcher_id=1)


async def test_other_researcher_raises_forbidden(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    methodology, _ = await _seed_methodology_with_scales(db_session, ["A"])
    survey = await _seed_survey(db_session, methodology, researcher_id=2)
    await db_session.commit()
    service = _make_analytics_service(db_session)
    with pytest.raises(ForbiddenError):
        await service.get_survey_analytics(survey.id, researcher_id=1)


async def test_admin_bypass_when_researcher_id_none(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    methodology, _ = await _seed_methodology_with_scales(db_session, ["A"])
    survey = await _seed_survey(db_session, methodology, researcher_id=2)
    await db_session.commit()
    service = _make_analytics_service(db_session)
    result = await service.get_survey_analytics(survey.id, researcher_id=None)
    assert result["total_invited"] == 0
    assert result["total_completed"] == 0


async def test_insufficient_data_below_3_sessions(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    methodology, scales = await _seed_methodology_with_scales(
        db_session, ["Тревожность", "Перфекционизм"]
    )
    survey = await _seed_survey(db_session, methodology)
    inv1 = await _add_invitation(db_session, survey, "Инжиниринг", used=True)
    inv2 = await _add_invitation(db_session, survey, "Маркетинг", used=True)
    await _add_completed_session_with_scores(
        db_session, survey, scales, [Decimal("78"), Decimal("40")], inv1
    )
    await _add_completed_session_with_scores(
        db_session, survey, scales, [Decimal("60"), Decimal("55")], inv2
    )
    await db_session.commit()

    service = _make_analytics_service(db_session)
    result = await service.get_survey_analytics(survey.id, researcher_id=1)

    assert result["total_invited"] == 2
    assert result["total_completed"] == 2
    assert result["is_sufficient"] is False
    assert result["insufficient_note"] == INSUFFICIENT_NOTE
    assert result["scale_averages"] is None
    assert result["scale_distribution"] is None
    assert result["department_comparison"] is None


async def test_full_analytics_with_3_sessions(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    methodology, scales = await _seed_methodology_with_scales(
        db_session, ["Тревожность", "Оптимизм"]
    )
    survey = await _seed_survey(db_session, methodology)
    for value_anx, value_opt in [(78, 40), (80, 50), (60, 70)]:
        inv = await _add_invitation(db_session, survey, "Инжиниринг", used=True)
        await _add_completed_session_with_scores(
            db_session,
            survey,
            scales,
            [Decimal(value_anx), Decimal(value_opt)],
            inv,
        )
    await db_session.commit()

    service = _make_analytics_service(db_session)
    result = await service.get_survey_analytics(survey.id, researcher_id=1)

    assert result["is_sufficient"] is True
    assert result["total_invited"] == 3
    assert result["total_completed"] == 3
    assert result["completion_rate"] == pytest.approx(1.0)

    averages = result["scale_averages"]
    anx_scale_id = scales[0].id
    opt_scale_id = scales[1].id
    assert averages[anx_scale_id]["scale_name"] == "Тревожность"
    assert averages[anx_scale_id]["average"] == pytest.approx(
        (78 + 80 + 60) / 3, abs=0.01
    )
    assert averages[opt_scale_id]["average"] == pytest.approx(
        (40 + 50 + 70) / 3, abs=0.01
    )

    distribution = result["scale_distribution"]
    assert distribution[anx_scale_id]["high"] == 2
    assert distribution[anx_scale_id]["mid"] == 1
    assert distribution[anx_scale_id]["low"] == 0


async def test_department_comparison_requires_3_per_dept(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    methodology, scales = await _seed_methodology_with_scales(
        db_session, ["Шкала А"]
    )
    survey = await _seed_survey(db_session, methodology)

    for value in [50, 60, 70]:
        inv = await _add_invitation(db_session, survey, "Инжиниринг", used=True)
        await _add_completed_session_with_scores(
            db_session, survey, scales, [Decimal(value)], inv
        )
    inv_mk = await _add_invitation(db_session, survey, "Маркетинг", used=True)
    await _add_completed_session_with_scores(
        db_session, survey, scales, [Decimal("80")], inv_mk
    )
    await db_session.commit()

    service = _make_analytics_service(db_session)
    result = await service.get_survey_analytics(survey.id, researcher_id=1)

    assert result["is_sufficient"] is True
    comparison = result["department_comparison"]
    assert len(comparison) == 1
    assert comparison[0]["department"] == "Инжиниринг"
    assert comparison[0]["respondents_count"] == 3
    assert comparison[0]["scale_averages"][scales[0].id] == pytest.approx(
        60.0, abs=0.01
    )


async def test_department_comparison_two_departments_both_qualify(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    methodology, scales = await _seed_methodology_with_scales(
        db_session, ["Шкала А"]
    )
    survey = await _seed_survey(db_session, methodology)

    for value in [50, 60, 70]:
        inv = await _add_invitation(db_session, survey, "Инжиниринг", used=True)
        await _add_completed_session_with_scores(
            db_session, survey, scales, [Decimal(value)], inv
        )
    for value in [40, 45, 50]:
        inv = await _add_invitation(db_session, survey, "Маркетинг", used=True)
        await _add_completed_session_with_scores(
            db_session, survey, scales, [Decimal(value)], inv
        )
    await db_session.commit()

    service = _make_analytics_service(db_session)
    result = await service.get_survey_analytics(survey.id, researcher_id=1)

    comparison = result["department_comparison"]
    depts = {row["department"] for row in comparison}
    assert depts == {"Инжиниринг", "Маркетинг"}


async def test_completion_rate_zero_when_no_invitations(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    methodology, scales = await _seed_methodology_with_scales(db_session, ["A"])
    survey = await _seed_survey(db_session, methodology)
    for _ in range(MIN_SESSIONS_FOR_AGGREGATES):
        await _add_completed_session_with_scores(
            db_session, survey, scales, [Decimal("50")]
        )
    await db_session.commit()

    service = _make_analytics_service(db_session)
    result = await service.get_survey_analytics(survey.id, researcher_id=1)

    assert result["total_invited"] == 0
    assert result["completion_rate"] == 0.0
    assert result["is_sufficient"] is True
