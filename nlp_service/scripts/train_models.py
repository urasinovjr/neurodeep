import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.features import extract_features  # noqa: E402
from app.ridge import FEATURE_KEYS, MODELS_DIR  # noqa: E402

SEED_PATH = ROOT / "data" / "seed_train.json"
RIDGE_ALPHA = 1.0
CV_MIN_SAMPLES = 6


def embed_texts(texts: list[str]) -> NDArray[np.float32]:
    tokenizer = AutoTokenizer.from_pretrained(
        settings.MODEL_NAME, cache_dir=settings.MODEL_CACHE_DIR
    )
    model = AutoModel.from_pretrained(
        settings.MODEL_NAME, cache_dir=settings.MODEL_CACHE_DIR
    )
    model.eval()
    out: list[NDArray[np.float32]] = []
    for text in texts:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
        out.append(outputs.last_hidden_state[0, 0, :].cpu().numpy().astype(np.float32))
    return np.array(out, dtype=np.float32)


def vectorize_corpus(texts: list[str]) -> NDArray[np.float32]:
    embs = embed_texts(texts)
    feats: list[list[float]] = []
    for text in texts:
        f = extract_features(text)
        feats.append([float(f[k]) for k in FEATURE_KEYS])
    feats_arr = np.array(feats, dtype=np.float32)
    return np.concatenate([embs, feats_arr], axis=1)


def confidence_from_residuals(model: Ridge, x: NDArray[np.float32], y: NDArray[np.float32]) -> tuple[float, float]:
    n = len(y)
    if n >= CV_MIN_SAMPLES:
        n_splits = min(3, n)
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        residuals: list[float] = []
        for train_idx, test_idx in kf.split(x):
            m = Ridge(alpha=RIDGE_ALPHA)
            m.fit(x[train_idx], y[train_idx])
            pred = m.predict(x[test_idx])
            residuals.extend(np.abs(pred - y[test_idx]).tolist())
        mae = float(np.mean(residuals))
    else:
        train_pred = model.predict(x)
        mae = float(np.mean(np.abs(train_pred - y)))
    confidence = max(0.0, 1.0 - mae / 100.0)
    return mae, confidence


def train_per_scale(samples: list[dict]) -> dict[int, dict]:
    texts = [s["text"] for s in samples]
    print(f"[train] vectorizing {len(texts)} samples...")
    matrix = vectorize_corpus(texts)

    by_scale: dict[int, list[float | None]] = {}
    for i, s in enumerate(samples):
        for sid_str, score in s.get("scores", {}).items():
            sid = int(sid_str)
            if sid not in by_scale:
                by_scale[sid] = [None] * len(samples)
            by_scale[sid][i] = float(score)

    bundles: dict[int, dict] = {}
    for sid, ys in by_scale.items():
        mask = np.array([y is not None for y in ys])
        if int(mask.sum()) < 3:
            print(f"[train] scale {sid}: <3 labelled samples, skipping")
            continue
        x = matrix[mask]
        y = np.array([y for y in ys if y is not None], dtype=np.float32)
        model = Ridge(alpha=RIDGE_ALPHA)
        model.fit(x, y)
        mae, confidence = confidence_from_residuals(model, x, y)
        bundles[sid] = {
            "model": model,
            "confidence": confidence,
            "n_samples": int(mask.sum()),
            "mae": mae,
        }
        print(
            f"[train] scale {sid}: trained on {int(mask.sum())} samples, "
            f"mae={mae:.2f}, confidence={confidence:.2f}"
        )
    return bundles


def save_bundles(bundles: dict[int, dict]) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for sid, bundle in bundles.items():
        path = MODELS_DIR / f"scale_{sid}.pkl"
        with path.open("wb") as f:
            pickle.dump(bundle, f)
        print(f"[train] saved {path}")


def main() -> None:
    if not SEED_PATH.exists():
        print(f"[train] seed not found: {SEED_PATH}")
        sys.exit(1)
    samples = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not samples:
        print("[train] seed is empty or malformed")
        sys.exit(1)
    bundles = train_per_scale(samples)
    save_bundles(bundles)
    print(f"[train] done; {len(bundles)} scales trained")


if __name__ == "__main__":
    main()
