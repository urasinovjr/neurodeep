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


async def test_create_methodology_returns_201_and_draft(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    response = await api_client.post(
        "/api/admin/methodologies",
        json={"name": "CBT", "category": "psychometric"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["name"] == "CBT"
    assert body["author_id"] == 1


async def test_list_methodologies_filters_by_status(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    await api_client.post(
        "/api/admin/methodologies", json={"name": "Pub", "category": "cbt"}
    )
    pub = await api_client.post(
        "/api/admin/methodologies", json={"name": "Drf", "category": "cbt"}
    )

    methodology_id = pub.json()["id"]
    db_session.expunge_all()
    obj = await db_session.get(Methodology, methodology_id)
    assert obj is not None
    obj.status = "published"
    await db_session.commit()

    drafts = await api_client.get("/api/admin/methodologies?status=draft")
    assert {m["name"] for m in drafts.json()} == {"Pub"}

    published = await api_client.get("/api/admin/methodologies?status=published")
    assert {m["name"] for m in published.json()} == {"Drf"}


async def test_list_methodologies_pagination_and_search(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    for name in ["Alpha", "Beta", "Gamma"]:
        await api_client.post(
            "/api/admin/methodologies", json={"name": name, "category": "cbt"}
        )

    page1 = await api_client.get("/api/admin/methodologies?limit=2&offset=0")
    page2 = await api_client.get("/api/admin/methodologies?limit=2&offset=2")
    assert len(page1.json()) == 2
    assert len(page2.json()) == 1

    found = await api_client.get("/api/admin/methodologies?search=alp")
    assert {m["name"] for m in found.json()} == {"Alpha"}


async def test_patch_methodology_only_draft(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    created = await api_client.post(
        "/api/admin/methodologies", json={"name": "M", "category": "cbt"}
    )
    methodology_id = created.json()["id"]

    patched = await api_client.patch(
        f"/api/admin/methodologies/{methodology_id}",
        json={"name": "M-edited"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "M-edited"


async def test_full_flow_create_3_scales_5_questions_publish(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    created = await api_client.post(
        "/api/admin/methodologies", json={"name": "Full", "category": "cbt"}
    )
    methodology_id = created.json()["id"]

    publish_too_early = await api_client.post(
        f"/api/admin/methodologies/{methodology_id}/publish"
    )
    assert publish_too_early.status_code == 422

    for i in range(3):
        scale_resp = await api_client.post(
            f"/api/admin/methodologies/{methodology_id}/scales",
            json={"name": f"Scale {i}", "order_index": i},
        )
        assert scale_resp.status_code == 201

    for i in range(5):
        question_resp = await api_client.post(
            f"/api/admin/methodologies/{methodology_id}/questions",
            json={"text": f"Question {i}?", "order_index": i},
        )
        assert question_resp.status_code == 201

    publish_ok = await api_client.post(
        f"/api/admin/methodologies/{methodology_id}/publish"
    )
    assert publish_ok.status_code == 200
    assert publish_ok.json()["status"] == "published"


async def test_archive_endpoint(
    db_session: AsyncSession, api_client: AsyncClient
) -> None:
    await _cleanup(db_session)
    created = await api_client.post(
        "/api/admin/methodologies", json={"name": "M", "category": "cbt"}
    )
    methodology_id = created.json()["id"]

    archived = await api_client.post(
        f"/api/admin/methodologies/{methodology_id}/archive"
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


async def test_publish_returns_404_for_unknown(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/admin/methodologies/9999999/publish"
    )
    assert response.status_code == 404
