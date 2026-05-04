from httpx import AsyncClient
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Methodology, Question, QuestionScale, Scale


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(sql_delete(QuestionScale))
    await session.execute(sql_delete(Question))
    await session.execute(sql_delete(Scale))
    await session.execute(sql_delete(Methodology))
    await session.commit()


async def _create_published(
    session: AsyncSession, name: str, scale_names: list[str], question_texts: list[str]
) -> Methodology:
    methodology = Methodology(name=name, category="cbt", status="published")
    session.add(methodology)
    await session.flush()
    session.add_all(
        [Scale(methodology_id=methodology.id, name=n) for n in scale_names]
    )
    session.add_all(
        [
            Question(methodology_id=methodology.id, text=t, order_index=i)
            for i, t in enumerate(question_texts)
        ]
    )
    await session.commit()
    return methodology


async def test_list_returns_only_published_with_scale_count(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    await _create_published(
        db_session, "Pub-A", ["S1", "S2", "S3"], ["Q1?", "Q2?"]
    )
    db_session.add(Methodology(name="Drf", category="cbt", status="draft"))
    db_session.add(Methodology(name="Arc", category="cbt", status="archived"))
    await db_session.commit()

    response = await api_client.get("/api/methodologies")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Pub-A"
    assert body[0]["scale_count"] == 3
    assert "description" not in body[0]


async def test_detail_returns_full_published(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = await _create_published(
        db_session,
        "Pub-Detail",
        ["S1", "S2"],
        ["Q1?", "Q2?", "Q3?"],
    )

    response = await api_client.get(f"/api/methodologies/{methodology.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Pub-Detail"
    assert body["status"] == "published"
    assert {s["name"] for s in body["scales"]} == {"S1", "S2"}
    assert {q["text"] for q in body["questions"]} == {"Q1?", "Q2?", "Q3?"}


async def test_detail_404_for_draft(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    methodology = Methodology(name="Drf", category="cbt", status="draft")
    db_session.add(methodology)
    await db_session.commit()

    response = await api_client.get(f"/api/methodologies/{methodology.id}")
    assert response.status_code == 404


async def test_detail_404_for_unknown(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/methodologies/9999999")
    assert response.status_code == 404
