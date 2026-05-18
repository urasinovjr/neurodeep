import secrets
import uuid

import pytest
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


async def _make_published_methodology(session: AsyncSession) -> Methodology:
    methodology = Methodology(name="M", category="cbt", status="published")
    session.add(methodology)
    await session.commit()
    return methodology


async def test_create_survey_returns_201_with_invite_token(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    response = await api_client.post(
        "/api/surveys",
        json={"methodology_id": methodology.id, "name": "Q1 Survey"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["name"] == "Q1 Survey"
    assert body["researcher_id"] == 1
    assert body["invite_token"] and len(body["invite_token"]) >= 16

    db_session.expunge_all()
    survey = await db_session.get(Survey, body["id"])
    assert survey is not None
    assert survey.invite_token == body["invite_token"]


async def test_create_survey_with_unpublished_methodology_returns_422(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="draft")
    db_session.add(methodology)
    await db_session.commit()

    response = await api_client.post(
        "/api/surveys",
        json={"methodology_id": methodology.id, "name": "Q1"},
    )
    assert response.status_code == 422


async def test_list_surveys_returns_only_own(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    other = User(
        email="other@test.local", password_hash="x", first_name="O", last_name="U",
        role=UserRole.RESEARCHER, status=UserStatus.ACTIVE,
    )
    db_session.add(other)
    await db_session.commit()

    db_session.add(Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="Mine", invite_token=secrets.token_urlsafe(24),
    ))
    db_session.add(Survey(
        researcher_id=other.id, methodology_id=methodology.id,
        name="Theirs", invite_token=secrets.token_urlsafe(24),
    ))
    await db_session.commit()

    response = await api_client.get("/api/surveys")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert {s["name"] for s in body["items"]} == {"Mine"}


async def test_list_surveys_filters_by_status(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    db_session.add(Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="Draft", invite_token=secrets.token_urlsafe(24), status="draft",
    ))
    db_session.add(Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="Active", invite_token=secrets.token_urlsafe(24), status="active",
    ))
    await db_session.commit()

    response = await api_client.get("/api/surveys?status=active")
    assert response.status_code == 200
    body = response.json()
    assert {s["name"] for s in body["items"]} == {"Active"}


async def test_get_survey_returns_detail_with_counts(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    survey = Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="Detail", invite_token=secrets.token_urlsafe(24),
    )
    db_session.add(survey)
    await db_session.commit()

    db_session.add_all([
        Invitation(survey_id=survey.id, token=uuid.uuid4()),
        Invitation(survey_id=survey.id, token=uuid.uuid4()),
    ])
    await db_session.commit()

    response = await api_client.get(f"/api/surveys/{survey.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == survey.id
    assert body["invited_count"] == 2
    assert body["completed_count"] == 0


async def test_get_survey_other_researcher_returns_403(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    other = User(
        email="other2@test.local", password_hash="x", first_name="O", last_name="U",
        role=UserRole.RESEARCHER, status=UserStatus.ACTIVE,
    )
    db_session.add(other)
    await db_session.commit()

    survey = Survey(
        researcher_id=other.id, methodology_id=methodology.id,
        name="Theirs", invite_token=secrets.token_urlsafe(24),
    )
    db_session.add(survey)
    await db_session.commit()

    response = await api_client.get(f"/api/surveys/{survey.id}")
    assert response.status_code == 403


async def test_patch_survey_updates_fields(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    survey = Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="Old", invite_token=secrets.token_urlsafe(24), status="draft",
    )
    db_session.add(survey)
    await db_session.commit()

    response = await api_client.patch(
        f"/api/surveys/{survey.id}",
        json={"name": "New", "welcome_message": "Hi"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "New"
    assert body["welcome_message"] == "Hi"


async def test_patch_archived_survey_returns_422(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    survey = Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="Old", invite_token=secrets.token_urlsafe(24), status="archived",
    )
    db_session.add(survey)
    await db_session.commit()

    response = await api_client.patch(
        f"/api/surveys/{survey.id}", json={"name": "New"}
    )
    assert response.status_code == 422


async def test_archive_survey_sets_status(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _make_published_methodology(db_session)

    survey = Survey(
        researcher_id=1, methodology_id=methodology.id,
        name="A", invite_token=secrets.token_urlsafe(24), status="active",
    )
    db_session.add(survey)
    await db_session.commit()

    response = await api_client.post(f"/api/surveys/{survey.id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"
