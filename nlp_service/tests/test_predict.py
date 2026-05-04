from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main as main_module
from app.main import PredictRequest


def _fake_embed(_text: str) -> Any:
    return np.zeros(768, dtype=np.float32)


def _fake_score(scale_id: int, _text: str, _embedding: Any) -> dict[str, float]:
    return {"value": 50.0 + scale_id, "confidence": 0.5}


def _fake_themes(_text: str) -> list[dict[str, Any]]:
    return [{"tag": "cbt", "score": 0.7}]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main_module, "_embed_cls", _fake_embed)
    monkeypatch.setattr(main_module, "predict_score", _fake_score)
    monkeypatch.setattr(main_module, "detect_themes", _fake_themes)
    return TestClient(main_module.app)


def test_predict_text_too_short_returns_422() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(text="abc", scale_ids=[1], methodology_id=1)


def test_predict_text_too_long_returns_422() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(text="x" * 5000, scale_ids=[1], methodology_id=1)


def test_predict_empty_scale_ids_returns_422() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(text="достаточно длинный", scale_ids=[], methodology_id=1)


def test_predict_returns_scores_for_all_scale_ids(client: TestClient) -> None:
    body = {
        "text": "достаточно длинный текст для проверки",
        "scale_ids": [1, 2, 3],
        "methodology_id": 1,
    }
    response = client.post("/predict", json=body)
    assert response.status_code == 200
    data = response.json()
    assert set(data["scores"].keys()) == {"1", "2", "3"}
    for sid_str in ["1", "2", "3"]:
        item = data["scores"][sid_str]
        assert 0.0 <= item["value"] <= 100.0
        assert 0.0 <= item["confidence"] <= 1.0
    assert data["themes"] == [{"tag": "cbt", "score": 0.7}]


def test_predict_invalid_body_returns_422_via_http(client: TestClient) -> None:
    response = client.post(
        "/predict",
        json={"text": "abc", "scale_ids": [1], "methodology_id": 1},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Некорректные данные запроса"
    assert isinstance(body.get("errors"), list)
    assert body["errors"]


def test_predict_deterministic_same_input_same_output(client: TestClient) -> None:
    body = {
        "text": "одинаковый текст для проверки детерминизма",
        "scale_ids": [1, 2],
        "methodology_id": 1,
    }
    r1 = client.post("/predict", json=body).json()
    r2 = client.post("/predict", json=body).json()
    assert r1 == r2


def test_predict_503_when_model_not_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(main_module._MODELS, "tokenizer", None)
    monkeypatch.setitem(main_module._MODELS, "model", None)
    monkeypatch.setattr(main_module, "predict_score", _fake_score)
    monkeypatch.setattr(main_module, "detect_themes", _fake_themes)

    cli = TestClient(main_module.app)
    response = cli.post(
        "/predict",
        json={
            "text": "достаточно длинный текст",
            "scale_ids": [1],
            "methodology_id": 1,
        },
    )
    assert response.status_code == 503
