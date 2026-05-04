import pickle
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import Ridge

import app.ridge as ridge_module
from app.ridge import FEATURE_KEYS, predict_score, unload_models, vectorize


def _fake_features(_text: str) -> dict[str, float]:
    return {k: 0.0 for k in FEATURE_KEYS}


def test_cold_start_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ridge_module, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(ridge_module, "extract_features", _fake_features)
    unload_models()

    embedding = np.zeros(768, dtype=np.float32)
    result = predict_score(99999, "тест", embedding)

    assert result["value"] == 50.0
    assert result["confidence"] == 0.0


def test_predict_with_model_clipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ridge_module, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(ridge_module, "extract_features", _fake_features)
    unload_models()

    rng = np.random.default_rng(42)
    x_train = rng.random((10, 768 + len(FEATURE_KEYS))).astype(np.float32)
    y_train = rng.random(10).astype(np.float32) * 100.0
    model = Ridge(alpha=1.0)
    model.fit(x_train, y_train)

    bundle = {"model": model, "confidence": 0.65, "n_samples": 10, "mae": 25.0}
    with (tmp_path / "scale_1.pkl").open("wb") as f:
        pickle.dump(bundle, f)

    embedding = np.zeros(768, dtype=np.float32)
    result = predict_score(1, "пример", embedding)

    assert 0.0 <= result["value"] <= 100.0
    assert result["confidence"] == pytest.approx(0.65)


def test_predict_clips_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ridge_module, "extract_features", _fake_features)
    unload_models()

    def fake_load(_scale_id: int) -> dict:
        return {
            "model": Ridge(alpha=1.0).fit(
                np.zeros((2, 768 + len(FEATURE_KEYS)), dtype=np.float32),
                np.array([150.0, 150.0], dtype=np.float32),
            ),
            "confidence": 0.5,
        }

    monkeypatch.setattr(ridge_module, "_load_model", fake_load)

    embedding = np.zeros(768, dtype=np.float32)
    result = predict_score(2, "пример", embedding)

    assert result["value"] == 100.0
    assert result["confidence"] == pytest.approx(0.5)


def test_vectorize_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ridge_module, "extract_features", _fake_features)

    embedding = np.zeros(768, dtype=np.float32)
    vec = vectorize("тест", embedding)

    assert vec.shape == (768 + len(FEATURE_KEYS),)
    assert vec.dtype == np.float32


def test_load_model_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ridge_module, "MODELS_DIR", tmp_path)
    unload_models()

    bundle = {"model": Ridge(alpha=1.0), "confidence": 0.4, "n_samples": 5, "mae": 60.0}
    with (tmp_path / "scale_3.pkl").open("wb") as f:
        pickle.dump(bundle, f)

    first = ridge_module._load_model(3)
    assert first is not None

    (tmp_path / "scale_3.pkl").unlink()
    second = ridge_module._load_model(3)
    assert second is first
