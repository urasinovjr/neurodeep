import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
)
from app.db.repositories import (
    InvitationRepository,
    PinabaArtifactRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
    UserProfileRepository,
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
    await session.flush()


def _unique_email() -> str:
    return f"sur-{uuid.uuid4().hex[:10]}@example.com"


async def _setup_user_methodology(session: AsyncSession) -> tuple[User, Methodology, Scale]:
    user = User(
        email=_unique_email(),
        password_hash="x",
        first_name="R",
        last_name="User",
    )
    session.add(user)
    methodology = Methodology(name="M", category="cbt", status="published")
    session.add(methodology)
    await session.flush()
    scale = Scale(methodology_id=methodology.id, name="S1", order_index=0)
    session.add(scale)
    await session.flush()
    return user, methodology, scale


async def test_survey_get_by_invite_token(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, _ = await _setup_user_methodology(db_session)
    repo = SurveyRepository(db_session)
    created = await repo.create(
        researcher_id=user.id,
        methodology_id=methodology.id,
        name="S",
        invite_token="invite-abc-123",
    )

    found = await repo.get_by_invite_token("invite-abc-123")
    assert found is not None
    assert found.id == created.id
    assert await repo.get_by_invite_token("missing") is None


async def test_survey_get_by_researcher_paginated(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, _ = await _setup_user_methodology(db_session)
    repo = SurveyRepository(db_session)
    for i in range(5):
        await repo.create(
            researcher_id=user.id,
            methodology_id=methodology.id,
            name=f"S{i}",
            invite_token=f"tok-{i}",
        )

    rows, total = await repo.get_by_researcher(user.id, limit=2, offset=0)
    assert total == 5
    assert len(rows) == 2


async def test_survey_get_active(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, _ = await _setup_user_methodology(db_session)
    repo = SurveyRepository(db_session)
    await repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="A", invite_token="t-a", status="active",
    )
    await repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="D", invite_token="t-d", status="draft",
    )

    rows = await repo.get_active()
    assert {s.name for s in rows} == {"A"}


async def test_invitation_get_by_token_and_count_completed(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, _ = await _setup_user_methodology(db_session)
    survey_repo = SurveyRepository(db_session)
    survey = await survey_repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="S", invite_token="t-survey",
    )
    inv_repo = InvitationRepository(db_session)
    used_token = uuid.uuid4()
    await inv_repo.create(survey_id=survey.id, token=used_token, used_at=datetime.now(UTC))
    await inv_repo.create(survey_id=survey.id, token=uuid.uuid4(), used_at=datetime.now(UTC))
    await inv_repo.create(survey_id=survey.id, token=uuid.uuid4())

    found = await inv_repo.get_by_token(used_token)
    assert found is not None and found.token == used_token

    count = await inv_repo.count_completed(survey.id)
    assert count == 2


async def test_session_get_by_invite_and_anon_and_completed_list(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    user, methodology, _ = await _setup_user_methodology(db_session)
    survey_repo = SurveyRepository(db_session)
    inv_repo = InvitationRepository(db_session)
    sess_repo = SurveySessionRepository(db_session)

    survey = await survey_repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="S", invite_token="t-sess",
    )
    invitation = await inv_repo.create(survey_id=survey.id, token=uuid.uuid4())
    anon_id = uuid.uuid4()
    s1 = await sess_repo.create(
        survey_id=survey.id,
        invitation_id=invitation.id,
        respondent_anon_id=anon_id,
        status="in_progress",
    )
    s2 = await sess_repo.create(
        survey_id=survey.id,
        respondent_anon_id=uuid.uuid4(),
        status="completed",
        completed_at=datetime.now(UTC),
    )
    s3 = await sess_repo.create(
        survey_id=survey.id,
        respondent_anon_id=uuid.uuid4(),
        status="completed",
        completed_at=datetime.now(UTC) - timedelta(hours=1),
    )

    found = await sess_repo.get_by_invite_and_anon(invitation.id, anon_id)
    assert found is not None and found.id == s1.id

    completed = await sess_repo.list_completed_for_survey(survey.id)
    assert {s.id for s in completed} == {s2.id, s3.id}
    assert completed[0].id == s2.id


async def test_scale_score_aggregate_avg_for_survey(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, scale = await _setup_user_methodology(db_session)
    survey_repo = SurveyRepository(db_session)
    sess_repo = SurveySessionRepository(db_session)
    score_repo = ScaleScoreRepository(db_session)

    survey = await survey_repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="S", invite_token="t-avg",
    )
    s1 = await sess_repo.create(
        survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
        status="completed", completed_at=datetime.now(UTC),
    )
    s2 = await sess_repo.create(
        survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
        status="completed", completed_at=datetime.now(UTC),
    )
    s3_in_progress = await sess_repo.create(
        survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
        status="in_progress",
    )
    await score_repo.bulk_create([
        ScaleScore(session_id=s1.id, scale_id=scale.id, value=Decimal("60"), confidence=Decimal("0.8")),
        ScaleScore(session_id=s2.id, scale_id=scale.id, value=Decimal("80"), confidence=Decimal("0.9")),
        ScaleScore(
            session_id=s3_in_progress.id, scale_id=scale.id,
            value=Decimal("10"), confidence=Decimal("0.5"),
        ),
    ])

    avgs = await score_repo.aggregate_avg_for_survey(survey.id)
    assert scale.id in avgs
    assert avgs[scale.id].quantize(Decimal("0.01")) == Decimal("70.00")
    assert all(s_id == scale.id for s_id in avgs.keys())


async def test_scale_score_distribution_low_mid_high(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, scale = await _setup_user_methodology(db_session)
    survey_repo = SurveyRepository(db_session)
    sess_repo = SurveySessionRepository(db_session)
    score_repo = ScaleScoreRepository(db_session)

    survey = await survey_repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="S", invite_token="t-dist",
    )

    sessions = []
    for value in [Decimal("10"), Decimal("20"), Decimal("50"), Decimal("70"), Decimal("90")]:
        s = await sess_repo.create(
            survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
            status="completed", completed_at=datetime.now(UTC),
        )
        sessions.append((s, value))
    await score_repo.bulk_create([
        ScaleScore(session_id=s.id, scale_id=scale.id, value=value, confidence=Decimal("0.5"))
        for s, value in sessions
    ])

    dist = await score_repo.distribution_low_mid_high(survey.id, scale.id)
    assert dist == {"low": 2, "mid": 1, "high": 2}


async def test_pinaba_get_by_uuid_and_expire_old(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, methodology, _ = await _setup_user_methodology(db_session)
    survey_repo = SurveyRepository(db_session)
    sess_repo = SurveySessionRepository(db_session)
    pin_repo = PinabaArtifactRepository(db_session)

    survey = await survey_repo.create(
        researcher_id=user.id, methodology_id=methodology.id,
        name="S", invite_token="t-pin",
    )
    s = await sess_repo.create(
        survey_id=survey.id, respondent_anon_id=uuid.uuid4(),
        status="completed", completed_at=datetime.now(UTC),
    )
    fresh_uuid = uuid.uuid4()
    expired_uuid = uuid.uuid4()
    await pin_repo.create(
        session_id=s.id, image_key="pinaba/fresh.png",
        public_uuid=fresh_uuid,
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    await pin_repo.create(
        session_id=s.id, image_key="pinaba/expired.png",
        public_uuid=expired_uuid,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    found = await pin_repo.get_by_uuid(fresh_uuid)
    assert found is not None and found.image_key == "pinaba/fresh.png"

    deleted = await pin_repo.expire_old(datetime.now(UTC))
    assert deleted == 1
    assert await pin_repo.get_by_uuid(expired_uuid) is None
    assert await pin_repo.get_by_uuid(fresh_uuid) is not None


async def test_user_profile_upsert(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    user, _, _ = await _setup_user_methodology(db_session)
    repo = UserProfileRepository(db_session)

    first = await repo.upsert(user_id=user.id, encrypted_data=b"v1", key_version=1)
    assert first.encrypted_data == b"v1"
    assert first.key_version == 1

    second = await repo.upsert(user_id=user.id, encrypted_data=b"v2", key_version=2)
    assert second.id == first.id
    assert second.encrypted_data == b"v2"
    assert second.key_version == 2

    fetched = await repo.get_by_user(user.id)
    assert fetched is not None and fetched.encrypted_data == b"v2"
