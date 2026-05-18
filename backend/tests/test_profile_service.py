import secrets
from decimal import Decimal

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

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
    MethodologyRepository,
    ScaleRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
)
from app.services.profile_service import (
    DEFAULT_DOMAIN,
    WHEEL_DOMAINS,
    ProfileService,
    assign_domain,
    compute_wheel_balance,
    level_from_value,
)


@pytest.mark.parametrize(
    "scale_name,expected",
    [
        ("Тревожность", "emotions"),
        ("Эмоциональная стабильность", "emotions"),
        ("Перфекционизм мышления", "thinking"),
        ("Когнитивный контроль", "thinking"),
        ("Соматизация", "body"),
        ("Усталость и сон", "body"),
        ("Близость в отношениях", "relationships"),
        ("Социальная коммуникация", "relationships"),
        ("Поиск смысла", "meaning"),
        ("Жизненные ценности", "meaning"),
    ],
)
def test_assign_domain_matches_keyword(scale_name: str, expected: str) -> None:
    assert assign_domain(scale_name) == expected


def test_assign_domain_unknown_keyword_returns_default() -> None:
    assert assign_domain("Совершенно нейтральная шкала") == DEFAULT_DOMAIN


def test_assign_domain_case_insensitive() -> None:
    assert assign_domain("ТРЕВОЖНОСТЬ") == "emotions"
    assert assign_domain("Перфекционизм") == "thinking"


def test_compute_wheel_balance_returns_all_5_domains_zeroed_for_empty() -> None:
    result = compute_wheel_balance([])
    assert set(result.keys()) == set(WHEEL_DOMAINS)
    assert all(v == 0.0 for v in result.values())


def test_compute_wheel_balance_avg_per_domain() -> None:
    scales = [
        {"scale_name": "Тревожность", "value": 60.0},
        {"scale_name": "Эмоциональная регуляция", "value": 80.0},
        {"scale_name": "Когнитивный контроль", "value": 40.0},
    ]
    result = compute_wheel_balance(scales)
    assert result["emotions"] == 70.0
    assert result["thinking"] == 40.0
    assert result["body"] == 0.0
    assert result["relationships"] == 0.0
    assert result["meaning"] == 0.0


def test_compute_wheel_balance_rounds_to_two_decimals() -> None:
    scales = [
        {"scale_name": "Тревожность", "value": 33.333},
        {"scale_name": "Стресс", "value": 33.334},
    ]
    result = compute_wheel_balance(scales)
    assert result["emotions"] == 33.33


def test_level_from_value_thresholds() -> None:
    assert level_from_value(0) == "low"
    assert level_from_value(33.99) == "low"
    assert level_from_value(34) == "mid"
    assert level_from_value(66.99) == "mid"
    assert level_from_value(67) == "high"
    assert level_from_value(100) == "high"


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
    session.add(researcher)
    await session.commit()


async def _seed_session_with_scores(
    db_session: AsyncSession,
    scale_specs: list[tuple[str, Decimal]],
) -> SurveySession:
    methodology = Methodology(name="Тест профиля", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()

    scales: list[Scale] = []
    for idx, (name, _) in enumerate(scale_specs):
        scale = Scale(
            methodology_id=methodology.id,
            name=name,
            order_index=idx,
        )
        db_session.add(scale)
        scales.append(scale)
    await db_session.flush()

    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="Survey",
        invite_token=secrets.token_urlsafe(24),
        status="completed",
    )
    db_session.add(survey)
    await db_session.flush()

    sess = SurveySession(survey_id=survey.id, status="completed")
    db_session.add(sess)
    await db_session.flush()

    for scale, (_, value) in zip(scales, scale_specs, strict=True):
        db_session.add(
            ScaleScore(
                session_id=sess.id,
                scale_id=scale.id,
                value=value,
                confidence=Decimal("0.85"),
            )
        )
    await db_session.commit()
    return sess


def _make_profile_service(db_session: AsyncSession) -> ProfileService:
    return ProfileService(
        session_repo=SurveySessionRepository(db_session),
        survey_repo=SurveyRepository(db_session),
        methodology_repo=MethodologyRepository(db_session),
        scale_repo=ScaleRepository(db_session),
        scale_score_repo=ScaleScoreRepository(db_session),
    )


async def test_build_profile_json_returns_4_required_keys(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    sess = await _seed_session_with_scores(
        db_session,
        [
            ("Тревожность", Decimal("78")),
            ("Перфекционизм", Decimal("45")),
        ],
    )
    service = _make_profile_service(db_session)

    result = await service.build_profile_json(sess.id)

    assert result is not None
    assert set(result.keys()) == {
        "scale_scores",
        "text_interpretation",
        "recommendations",
        "wheel_balance",
    }
    assert isinstance(result["scale_scores"], list)
    assert isinstance(result["text_interpretation"], str)
    assert isinstance(result["recommendations"], list)
    assert isinstance(result["wheel_balance"], dict)


async def test_build_profile_json_deterministic(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    sess = await _seed_session_with_scores(
        db_session,
        [
            ("Тревожность", Decimal("78")),
            ("Перфекционизм", Decimal("45")),
            ("Соматизация", Decimal("20")),
        ],
    )
    service = _make_profile_service(db_session)

    first = await service.build_profile_json(sess.id)
    second = await service.build_profile_json(sess.id)

    assert first == second


async def test_build_profile_json_text_interpretation_contains_scale_value(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    sess = await _seed_session_with_scores(
        db_session,
        [("Тревожность", Decimal("78"))],
    )
    service = _make_profile_service(db_session)

    result = await service.build_profile_json(sess.id)

    assert result is not None
    assert "78" in result["text_interpretation"]
    assert "Тревожность" in result["text_interpretation"]


async def test_build_profile_json_wheel_balance_groups_by_domain(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    sess = await _seed_session_with_scores(
        db_session,
        [
            ("Тревожность", Decimal("60")),
            ("Эмоциональная регуляция", Decimal("80")),
            ("Когнитивный контроль", Decimal("40")),
        ],
    )
    service = _make_profile_service(db_session)

    result = await service.build_profile_json(sess.id)

    assert result is not None
    wheel = result["wheel_balance"]
    assert set(wheel.keys()) == set(WHEEL_DOMAINS)
    assert wheel["emotions"] == 70.0
    assert wheel["thinking"] == 40.0
    assert wheel["body"] == 0.0


async def test_build_profile_json_recommendations_for_high_scores(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    sess = await _seed_session_with_scores(
        db_session,
        [
            ("Тревожность", Decimal("85")),
            ("Перфекционизм", Decimal("90")),
        ],
    )
    service = _make_profile_service(db_session)

    result = await service.build_profile_json(sess.id)

    assert result is not None
    recs_text = " ".join(result["recommendations"])
    assert "Тревожность" in recs_text or "Перфекционизм" in recs_text


async def test_build_profile_json_scale_scores_include_level(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    sess = await _seed_session_with_scores(
        db_session,
        [
            ("Тревожность", Decimal("78")),
            ("Перфекционизм", Decimal("45")),
            ("Соматизация", Decimal("20")),
        ],
    )
    service = _make_profile_service(db_session)

    result = await service.build_profile_json(sess.id)

    assert result is not None
    by_name = {s["scale_name"]: s for s in result["scale_scores"]}
    assert by_name["Тревожность"]["level"] == "high"
    assert by_name["Перфекционизм"]["level"] == "mid"
    assert by_name["Соматизация"]["level"] == "low"


async def test_build_profile_json_returns_none_for_missing_session(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    import uuid as _uuid

    service = _make_profile_service(db_session)
    result = await service.build_profile_json(_uuid.uuid4())

    assert result is None


async def test_build_profile_json_returns_none_when_no_scores(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="S",
        invite_token=secrets.token_urlsafe(24),
        status="completed",
    )
    db_session.add(survey)
    await db_session.flush()
    sess = SurveySession(survey_id=survey.id, status="completed")
    db_session.add(sess)
    await db_session.commit()

    service = _make_profile_service(db_session)
    result = await service.build_profile_json(sess.id)

    assert result is None
