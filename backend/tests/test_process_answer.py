import secrets
from collections.abc import AsyncIterator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
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
from app.tasks import process_answer as pa


@pytest_asyncio.fixture(autouse=True)
async def _isolated_session_local(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[None]:
    eng = create_async_engine(settings.DATABASE_URL, future=True)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(pa, "AsyncSessionLocal", factory)
    try:
        yield
    finally:
        await eng.dispose()


async def _cleanup(db: AsyncSession) -> None:
    await db.execute(sql_delete(ScaleScore))
    await db.execute(sql_delete(PinabaArtifact))
    await db.execute(sql_delete(SurveySession))
    await db.execute(sql_delete(Invitation))
    await db.execute(sql_delete(Survey))
    await db.execute(sql_delete(UserProfile))
    await db.execute(sql_delete(QuestionScale))
    await db.execute(sql_delete(Question))
    await db.execute(sql_delete(Scale))
    await db.execute(sql_delete(Methodology))
    await db.execute(sql_delete(AuditLog))
    await db.execute(sql_delete(Session))
    await db.execute(sql_delete(User))
    db.add(
        User(
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
    )
    await db.commit()


async def _seed_session_with_question(
    db: AsyncSession,
) -> tuple[SurveySession, Question, list[Scale]]:
    methodology = Methodology(name="M", category="cbt", status="published")
    db.add(methodology)
    await db.flush()
    scales = [
        Scale(
            methodology_id=methodology.id,
            name="A",
            order_index=0,
            min_value=0,
            max_value=100,
        ),
        Scale(
            methodology_id=methodology.id,
            name="B",
            order_index=1,
            min_value=0,
            max_value=100,
        ),
    ]
    db.add_all(scales)
    await db.flush()
    question = Question(methodology_id=methodology.id, text="Q1", order_index=0)
    db.add(question)
    await db.flush()
    db.add(
        QuestionScale(
            question_id=question.id,
            scale_id=scales[0].id,
            weight=Decimal("1.00"),
        )
    )
    db.add(
        QuestionScale(
            question_id=question.id,
            scale_id=scales[1].id,
            weight=Decimal("0.50"),
        )
    )
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="S",
        invite_token=secrets.token_urlsafe(24),
        status="active",
    )
    db.add(survey)
    await db.flush()
    survey_session = SurveySession(
        survey_id=survey.id,
        status="in_progress",
        next_question_index=1,
    )
    db.add(survey_session)
    await db.commit()
    return survey_session, question, scales


def _patch_redis(monkeypatch: pytest.MonkeyPatch, redis_mock: AsyncMock) -> None:
    monkeypatch.setattr(pa, "make_redis_client", lambda: redis_mock)


def _make_httpx_response(payload: dict) -> httpx.Response:
    request = httpx.Request("POST", "http://nlp.test/predict")
    return httpx.Response(200, json=payload, request=request)


def _patch_httpx_post(monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> AsyncMock:
    post_mock = AsyncMock(return_value=response)

    class _ClientShim:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def post(self, *args, **kwargs):
            return await post_mock(*args, **kwargs)

    monkeypatch.setattr(pa.httpx, "AsyncClient", _ClientShim)
    return post_mock


@pytest.mark.asyncio
async def test_process_answer_success_writes_scores_and_deletes_redis_key(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    survey_session, question, scales = await _seed_session_with_question(db_session)
    session_id = str(survey_session.id)

    redis_state: dict[str, str] = {f"answer:{session_id}:{question.id}": "длинный ответ"}

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(side_effect=lambda key: redis_state.get(key))
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock(side_effect=lambda key: redis_state.pop(key, None))
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    payload = {
        "scores": {
            str(scales[0].id): {"value": 72.5, "confidence": 0.4},
            str(scales[1].id): {"value": 30.0, "confidence": 0.2},
        },
        "themes": [],
    }
    post_mock = _patch_httpx_post(monkeypatch, _make_httpx_response(payload))

    result = await pa._process_answer_async(session_id, question.id)

    assert result == {"status": "ok", "scores_count": 2}
    assert post_mock.await_count == 1
    redis_mock.setex.assert_awaited_once()
    args, _ = redis_mock.setex.await_args
    assert args[0] == f"processed:{session_id}:{question.id}"
    assert args[1] == pa.PROCESSED_TTL_SECONDS
    redis_mock.delete.assert_awaited_once_with(f"answer:{session_id}:{question.id}")
    assert f"answer:{session_id}:{question.id}" not in redis_state

    db_session.expunge_all()
    rows = (
        await db_session.execute(
            select(ScaleScore).where(ScaleScore.session_id == survey_session.id)
        )
    ).scalars().all()
    assert {(r.scale_id, r.value) for r in rows} == {
        (scales[0].id, Decimal("72.50")),
        (scales[1].id, Decimal("30.00")),
    }


@pytest.mark.asyncio
async def test_process_answer_no_text_returns_error(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    survey_session, question, _ = await _seed_session_with_question(db_session)

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    result = await pa._process_answer_async(str(survey_session.id), question.id)
    assert result == {"status": "error_no_text"}


@pytest.mark.asyncio
async def test_process_answer_already_processed_skipped(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    survey_session, question, _ = await _seed_session_with_question(db_session)
    session_id = str(survey_session.id)

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value="1")
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    result = await pa._process_answer_async(session_id, question.id)
    assert result == {"status": "skipped"}


@pytest.mark.asyncio
async def test_process_answer_nlp_error_returns_error_nlp(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    survey_session, question, _ = await _seed_session_with_question(db_session)
    session_id = str(survey_session.id)

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(
        side_effect=lambda key: "ответ" if key.startswith("answer:") else None
    )
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    failing_post = AsyncMock(
        side_effect=httpx.ConnectError("connection refused", request=None)
    )

    class _ClientShim:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def post(self, *a, **k):
            return await failing_post(*a, **k)

    monkeypatch.setattr(pa.httpx, "AsyncClient", _ClientShim)

    result = await pa._process_answer_async(session_id, question.id)
    assert result == {"status": "error_nlp"}


@pytest.mark.asyncio
async def test_process_answer_clamps_out_of_range_scores(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    survey_session, question, scales = await _seed_session_with_question(db_session)
    session_id = str(survey_session.id)

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(
        side_effect=lambda key: "ответ" if key.startswith("answer:") else None
    )
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    payload = {
        "scores": {
            str(scales[0].id): {"value": 150.0, "confidence": 1.5},
            str(scales[1].id): {"value": -10.0, "confidence": -0.2},
        },
        "themes": [],
    }
    _patch_httpx_post(monkeypatch, _make_httpx_response(payload))

    result = await pa._process_answer_async(session_id, question.id)
    assert result["status"] == "ok"

    db_session.expunge_all()
    rows = (
        await db_session.execute(
            select(ScaleScore).where(ScaleScore.session_id == survey_session.id)
        )
    ).scalars().all()
    by_scale = {r.scale_id: r for r in rows}
    assert by_scale[scales[0].id].value == Decimal("100.00")
    assert by_scale[scales[0].id].confidence == Decimal("1.00")
    assert by_scale[scales[1].id].value == Decimal("0.00")
    assert by_scale[scales[1].id].confidence == Decimal("0.00")


@pytest.mark.asyncio
async def test_process_answer_filters_unknown_scale_ids(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    survey_session, question, scales = await _seed_session_with_question(db_session)
    session_id = str(survey_session.id)

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(
        side_effect=lambda key: "ответ" if key.startswith("answer:") else None
    )
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    payload = {
        "scores": {
            str(scales[0].id): {"value": 50.0, "confidence": 0.5},
            "9999": {"value": 80.0, "confidence": 0.9},
        },
        "themes": [],
    }
    _patch_httpx_post(monkeypatch, _make_httpx_response(payload))

    result = await pa._process_answer_async(session_id, question.id)
    assert result == {"status": "ok", "scores_count": 1}

    db_session.expunge_all()
    rows = (
        await db_session.execute(
            select(ScaleScore).where(ScaleScore.session_id == survey_session.id)
        )
    ).scalars().all()
    assert {r.scale_id for r in rows} == {scales[0].id}


@pytest.mark.asyncio
async def test_process_answer_no_question_scales_returns_error(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    question = Question(methodology_id=methodology.id, text="Q1", order_index=0)
    db_session.add(question)
    await db_session.flush()
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="S",
        invite_token=secrets.token_urlsafe(24),
        status="active",
    )
    db_session.add(survey)
    await db_session.flush()
    survey_session = SurveySession(
        survey_id=survey.id,
        status="in_progress",
    )
    db_session.add(survey_session)
    await db_session.commit()

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(
        side_effect=lambda key: "ответ" if key.startswith("answer:") else None
    )
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    result = await pa._process_answer_async(str(survey_session.id), question.id)
    assert result == {"status": "error_no_scales"}


@pytest.mark.asyncio
async def test_process_answer_bad_session_uuid_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(
        side_effect=lambda key: None if key.startswith("processed:") else "ответ"
    )
    redis_mock.aclose = AsyncMock()
    _patch_redis(monkeypatch, redis_mock)

    result = await pa._process_answer_async("not-a-uuid", 1)
    assert result == {"status": "error_bad_session_id"}


@pytest.mark.asyncio
async def test_submit_answer_dispatches_celery_task(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import AsyncMock as _AsyncMock

    from app.db.repositories import (
        AuditLogRepository,
        MethodologyRepository,
        QuestionRepository,
        ScaleScoreRepository,
        SurveyRepository,
        SurveySessionRepository,
    )
    from app.services.audit_service import AuditService
    from app.services.session_service import SurveySessionService

    await _cleanup(db_session)
    methodology = Methodology(name="M", category="cbt", status="published")
    db_session.add(methodology)
    await db_session.flush()
    question = Question(methodology_id=methodology.id, text="Q1", order_index=0)
    db_session.add(question)
    await db_session.flush()
    survey = Survey(
        researcher_id=1,
        methodology_id=methodology.id,
        name="S",
        invite_token=secrets.token_urlsafe(24),
        status="active",
    )
    db_session.add(survey)
    await db_session.flush()
    sess = SurveySession(survey_id=survey.id, status="in_progress")
    db_session.add(sess)
    await db_session.commit()

    delay_mock = MagicMock()
    monkeypatch.setattr(pa.process_answer, "delay", delay_mock)

    redis = _AsyncMock()
    service = SurveySessionService(
        survey_repo=SurveyRepository(db_session),
        session_repo=SurveySessionRepository(db_session),
        question_repo=QuestionRepository(db_session),
        scale_score_repo=ScaleScoreRepository(db_session),
        methodology_repo=MethodologyRepository(db_session),
        redis_client=redis,
        audit_service=AuditService(AuditLogRepository(db_session)),
    )

    await service.submit_answer(
        session_id=sess.id,
        question_id=question.id,
        text="ответ респондента",
    )
    await db_session.commit()

    delay_mock.assert_called_once_with(str(sess.id), question.id)
