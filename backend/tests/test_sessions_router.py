import secrets
import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
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


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    saved = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = saved


@pytest.fixture(autouse=True)
def _mock_process_answer_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    from app.tasks import process_answer as pa_module

    monkeypatch.setattr(pa_module.process_answer, "delay", MagicMock())


@pytest.fixture
def redis_mock() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
async def session_api_client(
    api_client: AsyncClient, redis_mock: AsyncMock
) -> AsyncClient:
    from app.api.deps import get_redis
    from app.main import app

    async def fake_get_redis():
        yield redis_mock

    app.dependency_overrides[get_redis] = fake_get_redis
    return api_client


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
    admin = User(
        id=1,
        email="admin@test.local",
        password_hash="x",
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        failed_login_attempts=0,
    )
    session.add(admin)
    await session.commit()


async def _make_active_survey(
    db_session: AsyncSession, n_questions: int = 2
) -> tuple[Survey, list[Question]]:
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    questions = [
        Question(methodology_id=methodology.id, text=f"Q{i + 1}", order_index=i)
        for i in range(n_questions)
    ]
    db_session.add_all(questions)
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="S",
        welcome_message="Привет!",
        invite_token=secrets.token_urlsafe(24),
        status="active",
    )
    db_session.add(survey)
    await db_session.commit()
    return survey, questions


async def test_survey_preview_returns_methodology_and_welcome(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    survey, _ = await _make_active_survey(db_session, n_questions=4)

    response = await session_api_client.get(
        f"/api/surveys/by-token/{survey.invite_token}"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "active"
    assert body["welcome_message"] == "Привет!"
    assert body["methodology"]["total_questions"] == 4
    assert body["methodology"]["name"] == "M"


async def test_survey_preview_unknown_token_returns_404(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    response = await session_api_client.get(
        "/api/surveys/by-token/no-such-token"
    )
    assert response.status_code == 404


async def test_survey_preview_archived_returns_410(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    db_session.add(Question(methodology_id=methodology.id, text="Q1", order_index=0))
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="A",
        invite_token=secrets.token_urlsafe(24),
        status="archived",
    )
    db_session.add(survey)
    await db_session.commit()

    response = await session_api_client.get(
        f"/api/surveys/by-token/{survey.invite_token}"
    )
    assert response.status_code == 410


async def test_start_session_returns_201_with_methodology_meta(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    survey, _ = await _make_active_survey(db_session, n_questions=3)

    response = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "consent_pending"
    assert body["welcome_message"] == "Привет!"
    assert body["methodology"]["total_questions"] == 3
    uuid.UUID(body["session_id"])


async def test_start_session_unknown_token_returns_404(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    response = await session_api_client.post(
        "/api/surveys/by-token/nonexistent-token/sessions"
    )
    assert response.status_code == 404


async def test_start_session_archived_survey_returns_410(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    db_session.add(Question(methodology_id=methodology.id, text="Q1", order_index=0))
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="A",
        invite_token=secrets.token_urlsafe(24),
        status="archived",
    )
    db_session.add(survey)
    await db_session.commit()

    response = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    assert response.status_code == 410


async def test_consent_returns_first_question_and_in_progress(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]

    response = await session_api_client.post(
        f"/api/surveys/sessions/{session_id}/consent"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["next_question_index"] == 0
    assert body["next_question"]["id"] == questions[0].id
    assert body["next_question"]["text"] == "Q1"


async def test_state_returns_progress_percent_and_next_question(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session, n_questions=4)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id}/consent")

    response = await session_api_client.get(
        f"/api/surveys/sessions/{session_id}/state"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_questions"] == 4
    assert body["next_question_index"] == 0
    assert body["progress_percent"] == 0
    assert body["next_question"]["id"] == questions[0].id
    assert body["invite_token"] == survey.invite_token


async def test_answer_returns_202_without_text_field(
    db_session: AsyncSession,
    session_api_client: AsyncClient,
    redis_mock: AsyncMock,
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id}/consent")

    response = await session_api_client.post(
        f"/api/surveys/sessions/{session_id}/answer",
        json={"question_id": questions[0].id, "text": "длинный ответ"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert "text" not in body
    assert body["status"] == "processing"
    assert body["session_status"] == "in_progress"
    assert body["next_question_index"] == 1


async def test_answer_writes_to_redis_with_ttl_3600(
    db_session: AsyncSession,
    session_api_client: AsyncClient,
    redis_mock: AsyncMock,
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id}/consent")

    await session_api_client.post(
        f"/api/surveys/sessions/{session_id}/answer",
        json={"question_id": questions[0].id, "text": "содержание"},
    )

    redis_mock.setex.assert_awaited_once_with(
        f"answer:{session_id}:{questions[0].id}",
        3600,
        "содержание",
    )


async def test_answer_last_question_marks_session_completed(
    db_session: AsyncSession,
    session_api_client: AsyncClient,
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session, n_questions=1)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id}/consent")

    response = await session_api_client.post(
        f"/api/surveys/sessions/{session_id}/answer",
        json={"question_id": questions[0].id, "text": "финальный ответ"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["session_status"] == "completed"


async def test_answer_too_short_returns_422(
    db_session: AsyncSession,
    session_api_client: AsyncClient,
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id}/consent")

    response = await session_api_client.post(
        f"/api/surveys/sessions/{session_id}/answer",
        json={"question_id": questions[0].id, "text": "короткий"},
    )
    assert response.status_code == 422


async def test_result_not_completed_returns_422(
    db_session: AsyncSession, session_api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    survey, _ = await _make_active_survey(db_session)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]

    response = await session_api_client.get(
        f"/api/surveys/sessions/{session_id}/result"
    )
    assert response.status_code == 422


async def test_result_returns_empty_scores_when_completed(
    db_session: AsyncSession,
    session_api_client: AsyncClient,
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session, n_questions=1)

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id}/consent")
    await session_api_client.post(
        f"/api/surveys/sessions/{session_id}/answer",
        json={"question_id": questions[0].id, "text": "ответ респондента"},
    )

    response = await session_api_client.get(
        f"/api/surveys/sessions/{session_id}/result"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["scores"] == []
    assert body["profile_text"] is None
    assert body["pinaba_url"] is None


async def test_result_renders_profile_text_when_scores_present(
    db_session: AsyncSession,
    session_api_client: AsyncClient,
) -> None:
    await _cleanup(db_session)
    survey, questions = await _make_active_survey(db_session, n_questions=1)

    scale = Scale(
        methodology_id=survey.methodology_id,
        name="Тестовая шкала",
        order_index=0,
        min_value=0,
        max_value=100,
    )
    db_session.add(scale)
    await db_session.commit()

    start = await session_api_client.post(
        f"/api/surveys/by-token/{survey.invite_token}/sessions"
    )
    session_id_str = start.json()["session_id"]
    await session_api_client.post(f"/api/surveys/sessions/{session_id_str}/consent")
    await session_api_client.post(
        f"/api/surveys/sessions/{session_id_str}/answer",
        json={"question_id": questions[0].id, "text": "ответ респондента"},
    )

    import uuid as _uuid
    from decimal import Decimal

    db_session.add(
        ScaleScore(
            session_id=_uuid.UUID(session_id_str),
            scale_id=scale.id,
            value=Decimal("78.00"),
            confidence=Decimal("0.50"),
        )
    )
    await db_session.commit()

    response = await session_api_client.get(
        f"/api/surveys/sessions/{session_id_str}/result"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile_text"] is not None
    assert "78" in body["profile_text"]
    assert "Тестовая шкала" in body["profile_text"]
    assert body["text_interpretation"] == body["profile_text"]
    assert len(body["scale_scores"]) == 1
    assert body["scale_scores"][0]["scale_name"] == "Тестовая шкала"
    assert body["scale_scores"][0]["level"] == "high"
    assert body["recommendations"]
    wheel = body["wheel_balance"]
    assert wheel is not None
    assert set(wheel.keys()) == {
        "emotions",
        "thinking",
        "body",
        "relationships",
        "meaning",
    }
