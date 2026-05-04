from decimal import Decimal

import pytest
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnprocessableError
from app.db.models import Methodology, Question, QuestionScale, Scale
from app.db.repositories import (
    MethodologyRepository,
    QuestionRepository,
    QuestionScaleRepository,
    ScaleRepository,
)
from app.schemas.methodology_schemas import (
    MethodologyCreateRequest,
    QuestionCreateRequest,
    QuestionScaleItem,
    QuestionScaleSetRequest,
    ScaleCreateRequest,
)
from app.services.methodology_service import MethodologyService


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(sql_delete(QuestionScale))
    await session.execute(sql_delete(Question))
    await session.execute(sql_delete(Scale))
    await session.execute(sql_delete(Methodology))
    await session.commit()


def _service(session: AsyncSession) -> MethodologyService:
    return MethodologyService(
        methodology_repo=MethodologyRepository(session),
        scale_repo=ScaleRepository(session),
        question_repo=QuestionRepository(session),
        question_scale_repo=QuestionScaleRepository(session),
    )


async def test_create_returns_draft(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    assert m.status == "draft"
    assert m.author_id == 1


async def test_publish_without_scales_raises(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    with pytest.raises(UnprocessableError) as exc:
        await service.publish(m.id, actor_id=1, is_admin=False)
    assert "шкал" in exc.value.detail


async def test_publish_with_3_scales_and_5_questions_ok(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )

    for i in range(3):
        await service.add_scale(
            m.id,
            ScaleCreateRequest(name=f"S{i}", order_index=i),
            actor_id=1,
            is_admin=False,
        )
    for i in range(5):
        await service.add_question(
            m.id,
            QuestionCreateRequest(text=f"Q{i}?", order_index=i),
            scale_weights=None,
            actor_id=1,
            is_admin=False,
        )

    published = await service.publish(m.id, actor_id=1, is_admin=False)
    assert published.status == "published"
    assert published.published_at is not None


async def test_publish_with_4_scales_2_questions_raises(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    for i in range(4):
        await service.add_scale(
            m.id, ScaleCreateRequest(name=f"S{i}"), actor_id=1, is_admin=False
        )
    for i in range(2):
        await service.add_question(
            m.id,
            QuestionCreateRequest(text=f"Q{i}?"),
            scale_weights=None,
            actor_id=1,
            is_admin=False,
        )
    with pytest.raises(UnprocessableError) as exc:
        await service.publish(m.id, actor_id=1, is_admin=False)
    assert "вопрос" in exc.value.detail.lower()


async def test_archive_with_active_surveys_raises_conflict(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )

    async def fake_count(_self: MethodologyService, _mid: int) -> int:
        return 2

    monkeypatch.setattr(MethodologyService, "_count_active_surveys", fake_count)

    with pytest.raises(ConflictError):
        await service.archive(m.id, actor_id=1, is_admin=False)


async def test_archive_without_active_surveys_ok(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    archived = await service.archive(m.id, actor_id=1, is_admin=False)
    assert archived.status == "archived"


async def test_add_scale_forbidden_for_other_author(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    with pytest.raises(ForbiddenError):
        await service.add_scale(
            m.id, ScaleCreateRequest(name="S"), actor_id=999, is_admin=False
        )


async def test_add_scale_admin_bypasses_author_check(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    scale = await service.add_scale(
        m.id, ScaleCreateRequest(name="S"), actor_id=999, is_admin=True
    )
    assert scale.methodology_id == m.id


async def test_publish_already_published_raises(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    for i in range(3):
        await service.add_scale(
            m.id, ScaleCreateRequest(name=f"S{i}"), actor_id=1, is_admin=False
        )
    for i in range(5):
        await service.add_question(
            m.id,
            QuestionCreateRequest(text=f"Q{i}?"),
            scale_weights=None,
            actor_id=1,
            is_admin=False,
        )
    await service.publish(m.id, actor_id=1, is_admin=False)
    with pytest.raises(UnprocessableError) as exc:
        await service.publish(m.id, actor_id=1, is_admin=False)
    assert "draft" in exc.value.detail.lower()


async def test_add_question_with_scale_weights(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    service = _service(db_session)
    m = await service.create(
        author_id=1, data=MethodologyCreateRequest(name="M", category="cbt")
    )
    s1 = await service.add_scale(
        m.id, ScaleCreateRequest(name="S1"), actor_id=1, is_admin=False
    )
    s2 = await service.add_scale(
        m.id, ScaleCreateRequest(name="S2"), actor_id=1, is_admin=False
    )
    q = await service.add_question(
        m.id,
        QuestionCreateRequest(text="Q?"),
        scale_weights=QuestionScaleSetRequest(
            weights=[
                QuestionScaleItem(scale_id=s1.id, weight=Decimal("0.7")),
                QuestionScaleItem(scale_id=s2.id, weight=Decimal("0.3")),
            ]
        ),
        actor_id=1,
        is_admin=False,
    )
    qs_repo = QuestionScaleRepository(db_session)
    weights = await qs_repo.get_weights_for_question(q.id)
    assert {(qs.scale_id, qs.weight) for qs in weights} == {
        (s1.id, Decimal("0.70")),
        (s2.id, Decimal("0.30")),
    }
