import pickle
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from app.features import extract_features

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FEATURE_KEYS: tuple[str, ...] = (
    "sentiment_pos",
    "sentiment_neg",
    "sentiment_neu",
    "length_chars",
    "length_tokens",
    "pronoun_i_ratio",
    "pronoun_we_ratio",
    "pronoun_you_ratio",
    "marker_should",
    "marker_always",
    "marker_never",
    "marker_body_part",
    "marker_family",
)

DEFAULT_VALUE = 50.0
DEFAULT_CONFIDENCE = 0.0

_models: dict[int, dict[str, Any]] = {}


def _model_path(scale_id: int) -> Path:
    return MODELS_DIR / f"scale_{scale_id}.pkl"


def _load_model(scale_id: int) -> dict[str, Any] | None:
    if scale_id in _models:
        return _models[scale_id]
    path = _model_path(scale_id)
    if not path.exists():
        return None
    with path.open("rb") as f:
        bundle = cast(dict[str, Any], pickle.load(f))
    _models[scale_id] = bundle
    return bundle


def unload_models() -> None:
    _models.clear()


def vectorize(text: str, embedding: NDArray[np.float32]) -> NDArray[np.float32]:
    feats = extract_features(text)
    lingv = np.array([feats[k] for k in FEATURE_KEYS], dtype=np.float32)
    return np.concatenate([embedding.astype(np.float32), lingv])


def predict_score(
    scale_id: int,
    text: str,
    embedding: NDArray[np.float32],
) -> dict[str, float]:
    bundle = _load_model(scale_id)
    if bundle is None:
        return {"value": DEFAULT_VALUE, "confidence": DEFAULT_CONFIDENCE}
    model = bundle["model"]
    confidence = float(bundle.get("confidence", DEFAULT_CONFIDENCE))
    vec = vectorize(text, embedding).reshape(1, -1)
    raw = float(model.predict(vec)[0])
    value = max(0.0, min(100.0, raw))
    return {"value": value, "confidence": confidence}
