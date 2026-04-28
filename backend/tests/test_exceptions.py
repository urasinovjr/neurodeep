from fastapi.testclient import TestClient

from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    GoneError,
    LockedError,
    NotFoundError,
    UnprocessableError,
)
from app.main import app

client = TestClient(app)


@app.get("/_test/notfound")
async def notfound_route():
    raise NotFoundError("X не найден")


@app.get("/_test/already-exists")
async def already_exists_route():
    raise AlreadyExistsError("Объект уже существует")


@app.get("/_test/authentication")
async def authentication_route():
    raise AuthenticationError("Неверный токен")


@app.get("/_test/forbidden")
async def forbidden_route():
    raise ForbiddenError("Недостаточно прав")


@app.get("/_test/conflict")
async def conflict_route():
    raise ConflictError("Конфликт состояния")


@app.get("/_test/gone")
async def gone_route():
    raise GoneError("Ссылка больше не действует")


@app.get("/_test/unprocessable")
async def unprocessable_route():
    raise UnprocessableError("Бизнес-правило нарушено")


@app.get("/_test/locked")
async def locked_route():
    raise LockedError("Аккаунт временно заблокирован")


def test_not_found_error_handler():
    response = client.get("/_test/notfound")
    assert response.status_code == 404
    assert response.json() == {"detail": "X не найден"}


def test_already_exists_error_handler():
    response = client.get("/_test/already-exists")
    assert response.status_code == 400
    assert response.json() == {"detail": "Объект уже существует"}


def test_authentication_error_handler():
    response = client.get("/_test/authentication")
    assert response.status_code == 401
    assert response.json() == {"detail": "Неверный токен"}


def test_forbidden_error_handler():
    response = client.get("/_test/forbidden")
    assert response.status_code == 403
    assert response.json() == {"detail": "Недостаточно прав"}


def test_conflict_error_handler():
    response = client.get("/_test/conflict")
    assert response.status_code == 409
    assert response.json() == {"detail": "Конфликт состояния"}


def test_gone_error_handler():
    response = client.get("/_test/gone")
    assert response.status_code == 410
    assert response.json() == {"detail": "Ссылка больше не действует"}


def test_unprocessable_error_handler():
    response = client.get("/_test/unprocessable")
    assert response.status_code == 422
    assert response.json() == {"detail": "Бизнес-правило нарушено"}


def test_locked_error_handler():
    response = client.get("/_test/locked")
    assert response.status_code == 423
    assert response.json() == {"detail": "Аккаунт временно заблокирован"}
