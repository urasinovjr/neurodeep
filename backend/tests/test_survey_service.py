import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
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
)
from app.db.repositories import (
    AuditLogRepository,
    InvitationRepository,
    MethodologyRepository,
    SurveyRepository,
    SurveySessionRepository,
)
from app.services.audit_service import AuditService
from app.services.survey_service import SurveyService


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
    await session.flush()


def _unique_email() -> str:
    return f"surv-{uuid.uuid4().hex[:10]}@example.com"


async def _make_user(session: AsyncSession) -> User:
    user = User(email=_unique_email(), password_hash="x", first_name="R", last_name="U")
    session.add(user)
    await session.flush()
    return user


async def _make_methodology(session: AsyncSession, status: str = "published") -> Methodology:
    m = Methodology(name="M", category="cbt", status=status)
    session.add(m)
    await session.flush()
    return m


def _make_service(session: AsyncSession) -> SurveyService:
    return SurveyService(
        survey_repo=SurveyRepository(session),
        invitation_repo=InvitationRepository(session),
        session_repo=SurveySessionRepository(session),
        methodology_repo=MethodologyRepository(session),
        audit_service=AuditService(AuditLogRepository(session)),
    )


async def test_create_generates_invite_token_and_audit(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=user.id, methodology_id=methodology.id, name="S1"
    )

    assert survey.id is not None
    assert survey.invite_token and len(survey.invite_token) >= 16
    assert survey.status == "draft"

    audit_repo = AuditLogRepository(db_session)
    rows, _ = await audit_repo.get_paginated(action="survey.created")
    assert len(rows) == 1
    assert rows[0].entity_id == survey.id
    assert rows[0].user_id == user.id


async def test_create_rejects_unpublished_methodology(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session, status="draft")
    service = _make_service(db_session)

    with pytest.raises(UnprocessableError):
        await service.create(
            researcher_id=user.id, methodology_id=methodology.id, name="S"
        )


async def test_create_rejects_inverted_dates(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    now = datetime.now(UTC)
    with pytest.raises(UnprocessableError):
        await service.create(
            researcher_id=user.id, methodology_id=methodology.id, name="S",
            start_date=now + timedelta(days=2), end_date=now,
        )


async def test_create_unknown_methodology_raises_not_found(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    service = _make_service(db_session)

    with pytest.raises(NotFoundError):
        await service.create(researcher_id=user.id, methodology_id=99999, name="S")


async def test_list_for_researcher_filters_status(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    s1 = await service.create(researcher_id=user.id, methodology_id=methodology.id, name="A")
    s2 = await service.create(researcher_id=user.id, methodology_id=methodology.id, name="B")
    s2.status = "active"
    await db_session.flush()
    _ = s1

    drafts, total_drafts = await service.list_for_researcher(user.id, status="draft")
    actives, total_actives = await service.list_for_researcher(user.id, status="active")

    assert {s.name for s in drafts} == {"A"}
    assert total_drafts == 1
    assert {s.name for s in actives} == {"B"}
    assert total_actives == 1


async def test_get_with_stats_returns_invited_and_completed_counts(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=user.id, methodology_id=methodology.id, name="S"
    )

    db_session.add_all([
        Invitation(survey_id=survey.id, token=uuid.uuid4()),
        Invitation(survey_id=survey.id, token=uuid.uuid4()),
        Invitation(survey_id=survey.id, token=uuid.uuid4()),
        SurveySession(
            survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
            status="completed", completed_at=datetime.now(UTC),
        ),
        SurveySession(
            survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
            status="completed", completed_at=datetime.now(UTC),
        ),
        SurveySession(
            survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
            status="in_progress",
        ),
    ])
    await db_session.flush()

    result, stats = await service.get_with_stats(survey.id, user.id)

    assert result.id == survey.id
    assert stats == {"invited": 3, "completed": 2}


async def test_get_with_stats_for_other_researcher_raises_forbidden(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    owner = await _make_user(db_session)
    other = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=owner.id, methodology_id=methodology.id, name="S"
    )

    with pytest.raises(ForbiddenError):
        await service.get_with_stats(survey.id, other.id)


async def test_get_by_id_for_other_researcher_raises_forbidden(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    owner = await _make_user(db_session)
    other = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=owner.id, methodology_id=methodology.id, name="S"
    )

    with pytest.raises(ForbiddenError):
        await service.get_by_id_for_researcher(survey.id, other.id)


async def test_archive_changes_status_and_logs_audit(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=user.id, methodology_id=methodology.id, name="S"
    )

    archived = await service.archive(survey.id, user.id)
    assert archived.status == "archived"

    audit_repo = AuditLogRepository(db_session)
    rows, _ = await audit_repo.get_paginated(action="survey.archived")
    assert len(rows) == 1
    assert rows[0].entity_id == survey.id


async def test_archive_for_other_researcher_raises_forbidden(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    owner = await _make_user(db_session)
    other = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=owner.id, methodology_id=methodology.id, name="S"
    )

    with pytest.raises(ForbiddenError):
        await service.archive(survey.id, other.id)


async def test_remind_pending_dispatches_celery_task_and_logs_audit(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=user.id, methodology_id=methodology.id, name="S"
    )

    class FakeAsyncResult:
        id = "fake-task-id"

    with patch("app.tasks.survey_tasks.send_survey_reminders.delay", return_value=FakeAsyncResult()):
        task_id = await service.remind_pending(survey.id, user.id)

    assert task_id == "fake-task-id"

    audit_repo = AuditLogRepository(db_session)
    rows, _ = await audit_repo.get_paginated(action="survey.invite_sent")
    assert len(rows) == 1
    assert rows[0].entity_id == survey.id


async def test_send_reminders_for_session_increments_counter(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user = await _make_user(db_session)
    methodology = await _make_methodology(db_session)
    service = _make_service(db_session)

    survey = await service.create(
        researcher_id=user.id, methodology_id=methodology.id, name="S"
    )

    db_session.add_all([
        Invitation(survey_id=survey.id, token=uuid.uuid4(), email="a@x.test"),
        Invitation(survey_id=survey.id, token=uuid.uuid4(), email="b@x.test"),
        Invitation(survey_id=survey.id, token=uuid.uuid4()),
        Invitation(
            survey_id=survey.id, token=uuid.uuid4(),
            email="c@x.test", used_at=datetime.now(UTC),
        ),
    ])
    await db_session.flush()

    from app.tasks.survey_tasks import _send_reminders_for_session

    sent = await _send_reminders_for_session(db_session, survey.id)
    assert sent == 2

    invitations_after = await db_session.execute(
        Invitation.__table__.select().where(Invitation.survey_id == survey.id)
    )
    rows = invitations_after.all()
    counts = {row.email: row.reminded_count for row in rows}
    assert counts.get("a@x.test") == 1
    assert counts.get("b@x.test") == 1
    assert counts.get(None) == 0
    assert counts.get("c@x.test") == 0
