import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    saved = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = saved


def _unique_email() -> str:
    return f"csrf-{uuid.uuid4().hex[:12]}@example.com"


async def _register_and_login(client: AsyncClient, db_session: AsyncSession):
    email = _unique_email()
    register_resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Valid123!",
            "first_name": "Csrf",
            "last_name": "Tester",
        },
    )
    assert register_resp.status_code == 201, register_resp.text
    await db_session.commit()
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "Valid123!"},
    )
    assert login_resp.status_code == 200, login_resp.text
    return login_resp


@pytest.mark.anyio
async def test_login_sets_csrf_cookie_not_httponly_and_body_contains_csrf(
    api_client: AsyncClient, db_session: AsyncSession
):
    login_resp = await _register_and_login(api_client, db_session)

    body = login_resp.json()
    assert body["access_token"]
    assert body["csrf_token"]

    set_cookie_headers = login_resp.headers.get_list("set-cookie")
    csrf_headers = [h for h in set_cookie_headers if h.startswith("csrf_token=")]
    refresh_headers = [h for h in set_cookie_headers if h.startswith("refresh_token=")]

    assert len(csrf_headers) == 1
    assert "HttpOnly" not in csrf_headers[0]
    assert "samesite=strict" in csrf_headers[0].lower()

    assert len(refresh_headers) == 1
    assert "httponly" in refresh_headers[0].lower()

    assert "csrf_token" in login_resp.cookies
    assert login_resp.cookies["csrf_token"] == body["csrf_token"]


@pytest.mark.anyio
async def test_refresh_without_csrf_header_returns_403(
    api_client: AsyncClient, db_session: AsyncSession
):
    await _register_and_login(api_client, db_session)

    refresh_resp = await api_client.post("/api/auth/refresh")
    assert refresh_resp.status_code == 403
    assert "CSRF" in refresh_resp.json()["detail"]


@pytest.mark.anyio
async def test_refresh_with_mismatched_csrf_header_returns_403(
    api_client: AsyncClient, db_session: AsyncSession
):
    await _register_and_login(api_client, db_session)

    refresh_resp = await api_client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": "totally-wrong-token"},
    )
    assert refresh_resp.status_code == 403
    assert "CSRF" in refresh_resp.json()["detail"]


@pytest.mark.anyio
async def test_refresh_with_matching_csrf_header_returns_200(
    api_client: AsyncClient, db_session: AsyncSession
):
    login_resp = await _register_and_login(api_client, db_session)
    csrf = login_resp.json()["csrf_token"]

    refresh_resp = await api_client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": csrf},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    body = refresh_resp.json()
    assert body["access_token"]
    assert body["csrf_token"]
    assert body["csrf_token"] != csrf

    new_set_cookie = refresh_resp.headers.get_list("set-cookie")
    csrf_headers = [h for h in new_set_cookie if h.startswith("csrf_token=")]
    assert len(csrf_headers) == 1
    assert "HttpOnly" not in csrf_headers[0]
