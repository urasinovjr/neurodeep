import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    GoneError,
    NotFoundError,
    UnprocessableError,
)
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
    AuditLogRepository,
    MethodologyRepository,
    QuestionRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
)
from app.services.audit_service import AuditService
from app.services.session_service import ANSWER_TTL_SECONDS, SurveySessionService


@pytest.fixture(autouse=True)
def _mock_process_answer_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    from app.tasks import process_answer as pa_module

    monkeypatch.setattr(pa_module.process_answer, "delay", MagicMock())


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


def _make_service(
    db_session: AsyncSession, redis_mock: AsyncMock | None = None
) -> tuple[SurveySessionService, AsyncMock]:
    redis = redis_mock or AsyncMock()
    return (
        SurveySessionService(
            survey_repo=SurveyRepository(db_session),
            session_repo=SurveySessionRepository(db_session),
            question_repo=QuestionRepository(db_session),
            scale_score_repo=ScaleScoreRepository(db_session),
            methodology_repo=MethodologyRepository(db_session),
            redis_client=redis,
            audit_service=AuditService(AuditLogRepository(db_session)),
        ),
        redis,
    )


async def _seed_active_survey(
    db_session: AsyncSession,
    survey_status: str = "active",
    question_texts: tuple[str, ...] = ("Q1", "Q2"),
) -> Survey:
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    for idx, t in enumerate(question_texts):
        db_session.add(
            Question(methodology_id=methodology.id, text=t, order_index=idx)
        )
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="S",
        welcome_message="Welcome",
        invite_token=secrets.token_urlsafe(24),
        status=survey_status,
    )
    db_session.add(survey)
    await db_session.commit()
    return survey


@pytest.mark.asyncio
async def test_start_by_token_creates_consent_pending_session(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)

    session, survey_out, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()

    assert session.status == "consent_pending"
    assert session.survey_id == survey.id
    assert session.next_question_index == 0
    assert isinstance(session.id, uuid.UUID)
    assert survey_out.id == survey.id
    assert len(questions) == 2


@pytest.mark.asyncio
async def test_start_by_token_unknown_raises_not_found(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    service, _ = _make_service(db_session)
    with pytest.raises(NotFoundError):
        await service.start_by_token("nonexistent-token")


@pytest.mark.asyncio
async def test_start_by_token_archived_raises_gone(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session, survey_status="archived")
    service, _ = _make_service(db_session)
    with pytest.raises(GoneError):
        await service.start_by_token(survey.invite_token)


@pytest.mark.asyncio
async def test_start_by_token_expired_end_date_raises_gone(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    db_session.add(Question(methodology_id=methodology.id, text="Q1", order_index=0))
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="Expired",
        invite_token=secrets.token_urlsafe(24),
        status="active",
        end_date=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(survey)
    await db_session.commit()

    service, _ = _make_service(db_session)
    with pytest.raises(GoneError):
        await service.start_by_token(survey.invite_token)


@pytest.mark.asyncio
async def test_start_by_token_methodology_without_questions_raises_422(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="Empty", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="X",
        invite_token=secrets.token_urlsafe(24),
        status="active",
    )
    db_session.add(survey)
    await db_session.commit()

    service, _ = _make_service(db_session)
    with pytest.raises(UnprocessableError):
        await service.start_by_token(survey.invite_token)


@pytest.mark.asyncio
async def test_give_consent_transitions_to_in_progress(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)
    session, *_ = await service.start_by_token(survey.invite_token)
    await db_session.commit()

    out, first = await service.give_consent(session.id)
    await db_session.commit()

    assert out.status == "in_progress"
    assert out.consent_given_at is not None
    assert out.started_at is not None
    assert first.order_index == 0
    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "session.consent_given")
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_give_consent_idempotent_when_already_in_progress(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)
    session, *_ = await service.start_by_token(survey.invite_token)
    await db_session.commit()
    await service.give_consent(session.id)
    await db_session.commit()

    out, first = await service.give_consent(session.id)
    assert out.status == "in_progress"
    assert first.order_index == 0


@pytest.mark.asyncio
async def test_submit_answer_writes_to_redis_and_increments_index(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, redis = _make_service(db_session)
    session, _, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()
    await service.give_consent(session.id)
    await db_session.commit()

    out = await service.submit_answer(
        session_id=session.id,
        question_id=questions[0].id,
        text="мой полный ответ",
    )
    await db_session.commit()

    redis.setex.assert_awaited_once_with(
        f"answer:{session.id}:{questions[0].id}",
        ANSWER_TTL_SECONDS,
        "мой полный ответ",
    )
    assert out.next_question_index == 1
    assert out.status == "in_progress"


@pytest.mark.asyncio
async def test_submit_answer_last_question_marks_completed(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session, question_texts=("Q1",))
    service, _ = _make_service(db_session)
    session, _, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()
    await service.give_consent(session.id)
    await db_session.commit()

    out = await service.submit_answer(
        session_id=session.id,
        question_id=questions[0].id,
        text="финальный ответ респондента",
    )
    await db_session.commit()

    assert out.status == "completed"
    assert out.completed_at is not None
    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "session.completed")
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_submit_answer_wrong_question_id_raises_422(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)
    session, _, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()
    await service.give_consent(session.id)
    await db_session.commit()

    with pytest.raises(UnprocessableError):
        await service.submit_answer(
            session_id=session.id,
            question_id=questions[1].id,
            text="развернутый ответ",
        )


@pytest.mark.asyncio
async def test_submit_answer_session_not_in_progress_raises_409(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)
    session, _, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()

    with pytest.raises(ConflictError):
        await service.submit_answer(
            session_id=session.id,
            question_id=questions[0].id,
            text="развернутый ответ",
        )


@pytest.mark.asyncio
async def test_submit_answer_too_short_raises_422(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)
    session, _, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()
    await service.give_consent(session.id)
    await db_session.commit()

    with pytest.raises(UnprocessableError):
        await service.submit_answer(
            session_id=session.id,
            question_id=questions[0].id,
            text="raz",
        )


@pytest.mark.asyncio
async def test_get_result_not_completed_raises_422(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session)
    service, _ = _make_service(db_session)
    session, *_ = await service.start_by_token(survey.invite_token)
    await db_session.commit()

    with pytest.raises(UnprocessableError):
        await service.get_result(session.id)


@pytest.mark.asyncio
async def test_get_result_completed_returns_empty_scores(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    survey = await _seed_active_survey(db_session, question_texts=("Q1",))
    service, _ = _make_service(db_session)
    session, _, questions = await service.start_by_token(survey.invite_token)
    await db_session.commit()
    await service.give_consent(session.id)
    await db_session.commit()
    await service.submit_answer(
        session_id=session.id,
        question_id=questions[0].id,
        text="окончательный ответ",
    )
    await db_session.commit()

    out, scores = await service.get_result(session.id)
    assert out.status == "completed"
    assert scores == []
