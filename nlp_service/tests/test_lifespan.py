import pytest

torch = pytest.importorskip("torch")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import _MODELS, app  # noqa: E402


def test_lifespan_loads_model_and_health_reports_ready():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model_loaded"] is True
        assert body["model_name"] == "DeepPavlov/rubert-base-cased"

        tokenizer = _MODELS["tokenizer"]
        model = _MODELS["model"]
        assert tokenizer is not None
        assert model is not None

        with torch.no_grad():
            inputs = tokenizer("тест", return_tensors="pt", truncation=True, max_length=128)
            outputs = model(**inputs)

        cls_embedding = outputs.last_hidden_state[:, 0, :]
        assert cls_embedding.shape == (1, 768)
