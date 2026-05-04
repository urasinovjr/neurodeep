from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.main as main_module


def _fake_embed(_text: str) -> Any:
    return np.zeros(768, dtype=np.float32)


def _fake_score(scale_id: int, _text: str, _embedding: Any) -> dict[str, float]:
    return {"value": 50.0 + scale_id, "confidence": 0.5}


def _fake_themes(_text: str) -> list[dict[str, Any]]:
    return [{"tag": "cbt", "score": 0.7}]


def _exploding_embed(_text: str) -> Any:
    raise RuntimeError("boom")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main_module, "_embed_cls", _fake_embed)
    monkeypatch.setattr(main_module, "predict_score", _fake_score)
    monkeypatch.setattr(main_module, "detect_themes", _fake_themes)
    return TestClient(main_module.app)


def test_health_includes_uptime_seconds(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "uptime_seconds" in body
    assert isinstance(body["uptime_seconds"], int | float)
    assert body["uptime_seconds"] >= 0


def test_metrics_content_type_and_format(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "version=0.0.4" in response.headers["content-type"]
    body = response.text
    assert "# HELP nlp_uptime_seconds" in body
    assert "# TYPE nlp_uptime_seconds gauge" in body
    assert "nlp_uptime_seconds " in body
    assert "nlp_predict_requests_total " in body
    assert "nlp_predict_errors_total " in body
    assert "nlp_predict_duration_seconds_sum " in body
    assert "nlp_model_loaded " in body


def test_metrics_increments_after_predict(client: TestClient) -> None:
    before = client.get("/metrics").text
    before_total = _extract_counter(before, "nlp_predict_requests_total")

    body = {
        "text": "достаточно длинный текст",
        "scale_ids": [1],
        "methodology_id": 1,
    }
    client.post("/predict", json=body)
    client.post("/predict", json=body)

    after = client.get("/metrics").text
    after_total = _extract_counter(after, "nlp_predict_requests_total")

    assert after_total - before_total == 2


def test_predict_failure_logs_and_increments_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "_embed_cls", _exploding_embed)
    monkeypatch.setattr(main_module, "predict_score", _fake_score)
    monkeypatch.setattr(main_module, "detect_themes", _fake_themes)
    cli = TestClient(main_module.app)

    before = cli.get("/metrics").text
    before_errors = _extract_counter(before, "nlp_predict_errors_total")

    response = cli.post(
        "/predict",
        json={
            "text": "достаточно длинный текст",
            "scale_ids": [1],
            "methodology_id": 1,
        },
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Ошибка предсказания"}

    after = cli.get("/metrics").text
    after_errors = _extract_counter(after, "nlp_predict_errors_total")
    assert after_errors - before_errors == 1


def _extract_counter(metrics_text: str, name: str) -> int:
    for line in metrics_text.splitlines():
        if line.startswith(f"{name} "):
            return int(line.split()[1])
    raise AssertionError(f"counter {name} not found")
