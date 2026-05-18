from decimal import Decimal

from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Invitation,
    Methodology,
    PinabaArtifact,
    Question,
    QuestionScale,
    Scale,
    ScaleScore,
    Survey,
    SurveySession,
)
from app.db.repositories import (
    MethodologyRepository,
    QuestionRepository,
    QuestionScaleRepository,
    ScaleRepository,
)


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(sql_delete(ScaleScore))
    await session.execute(sql_delete(PinabaArtifact))
    await session.execute(sql_delete(SurveySession))
    await session.execute(sql_delete(Invitation))
    await session.execute(sql_delete(Survey))
    await session.execute(sql_delete(QuestionScale))
    await session.execute(sql_delete(Question))
    await session.execute(sql_delete(Scale))
    await session.execute(sql_delete(Methodology))
    await session.flush()


async def test_methodology_get_published_filters_status(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    repo = MethodologyRepository(db_session)
    await repo.create(name="Pub", category="cbt", status="published")
    await repo.create(name="Draft", category="cbt", status="draft")

    rows = await repo.get_published()

    assert len(rows) == 1
    assert rows[0].name == "Pub"


async def test_methodology_get_drafts_by_author_filters(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    repo = MethodologyRepository(db_session)
    await repo.create(name="A1", category="cbt", status="draft", author_id=1)
    await repo.create(name="A2", category="cbt", status="draft", author_id=2)
    await repo.create(name="Pub", category="cbt", status="published", author_id=1)

    rows = await repo.get_drafts_by_author(author_id=1)

    assert {m.name for m in rows} == {"A1"}


async def test_get_by_id_with_scales_and_questions_no_n_plus_one(
    db_session: AsyncSession,
) -> None:
    await _cleanup(db_session)
    await db_session.commit()
    repo = MethodologyRepository(db_session)
    m = await repo.create(name="M", category="cbt")
    db_session.add_all([
        Scale(methodology_id=m.id, name="S1", order_index=0),
        Scale(methodology_id=m.id, name="S2", order_index=1),
        Question(methodology_id=m.id, text="Q1?", order_index=0),
        Question(methodology_id=m.id, text="Q2?", order_index=1),
    ])
    methodology_id = m.id
    await db_session.commit()
    db_session.expunge_all()

    loaded = await repo.get_by_id_with_scales_and_questions(methodology_id)
    assert loaded is not None

    scale_names = sorted(s.name for s in loaded.scales)
    question_texts = sorted(q.text for q in loaded.questions)

    assert scale_names == ["S1", "S2"]
    assert question_texts == ["Q1?", "Q2?"]


async def test_scale_get_by_methodology_orders_by_index(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    m_repo = MethodologyRepository(db_session)
    s_repo = ScaleRepository(db_session)
    m = await m_repo.create(name="M", category="cbt")
    await s_repo.bulk_create([
        Scale(methodology_id=m.id, name="C", order_index=2),
        Scale(methodology_id=m.id, name="A", order_index=0),
        Scale(methodology_id=m.id, name="B", order_index=1),
    ])

    rows = await s_repo.get_by_methodology(m.id)

    assert [s.name for s in rows] == ["A", "B", "C"]


async def test_question_get_by_theme_tags_filters(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    m_repo = MethodologyRepository(db_session)
    q_repo = QuestionRepository(db_session)
    m = await m_repo.create(name="M", category="cbt")
    db_session.add_all([
        Question(methodology_id=m.id, text="Q-cbt", order_index=0, theme_tags=["cbt"]),
        Question(methodology_id=m.id, text="Q-fam", order_index=1, theme_tags=["family"]),
        Question(methodology_id=m.id, text="Q-mix", order_index=2, theme_tags=["cbt", "gestalt"]),
        Question(methodology_id=m.id, text="Q-empty", order_index=3, theme_tags=None),
    ])
    await db_session.flush()

    cbt_only = await q_repo.get_by_theme_tags(m.id, ["cbt"])
    assert {q.text for q in cbt_only} == {"Q-cbt", "Q-mix"}

    fam_or_gestalt = await q_repo.get_by_theme_tags(m.id, ["family", "gestalt"])
    assert {q.text for q in fam_or_gestalt} == {"Q-fam", "Q-mix"}


async def test_question_scale_set_weights_replaces(db_session: AsyncSession) -> None:
    await _cleanup(db_session)
    m_repo = MethodologyRepository(db_session)
    s_repo = ScaleRepository(db_session)
    q_repo = QuestionRepository(db_session)
    qs_repo = QuestionScaleRepository(db_session)
    m = await m_repo.create(name="M", category="cbt")
    s1, s2, s3 = await s_repo.bulk_create([
        Scale(methodology_id=m.id, name="S1"),
        Scale(methodology_id=m.id, name="S2"),
        Scale(methodology_id=m.id, name="S3"),
    ])
    q = await q_repo.create(methodology_id=m.id, text="Q?")

    await qs_repo.set_weights(q.id, {s1.id: Decimal("0.8"), s2.id: Decimal("0.2")})
    first = await qs_repo.get_weights_for_question(q.id)
    assert {(qs.scale_id, qs.weight) for qs in first} == {
        (s1.id, Decimal("0.80")),
        (s2.id, Decimal("0.20")),
    }

    await qs_repo.set_weights(q.id, {s3.id: Decimal("1.0")})
    second = await qs_repo.get_weights_for_question(q.id)
    assert {(qs.scale_id, qs.weight) for qs in second} == {(s3.id, Decimal("1.00"))}
