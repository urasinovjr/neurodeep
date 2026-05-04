import re
from typing import Any

from app.core.config import settings

SENTIMENT_MODEL_NAME = "seara/rubert-tiny2-russian-sentiment"
SENTIMENT_LABELS = {0: "neutral", 1: "positive", 2: "negative"}

PRONOUN_GROUPS: dict[str, frozenset[str]] = {
    "i": frozenset({"я", "меня", "мне", "мной", "мною"}),
    "we": frozenset({"мы", "нас", "нам", "нами"}),
    "you": frozenset({
        "ты", "тебя", "тебе", "тобой", "тобою",
        "вы", "вас", "вам", "вами",
    }),
}

MARKER_WORDS: dict[str, frozenset[str]] = {
    "should": frozenset({
        "должен", "должна", "должно", "должны",
        "обязан", "обязана", "обязано", "обязаны",
        "надо", "нужно",
    }),
    "always": frozenset({"всегда", "постоянно", "вечно"}),
    "never": frozenset({"никогда", "никак"}),
    "body_part": frozenset({
        "голова", "головы", "голову",
        "грудь", "груди",
        "спина", "спину",
        "живот", "живота",
        "болит", "ноет", "давит", "колет", "тошнит", "ломит", "жжёт",
        "тяжесть",
    }),
    "family": frozenset({
        "родители", "родителей", "родителям",
        "мама", "маму", "мамой", "маме",
        "мать", "матери",
        "папа", "папу", "папой",
        "отец", "отца", "отцу",
        "брат", "брата",
        "сестра", "сестру",
        "жена", "жену",
        "муж", "мужа",
        "ребёнок", "ребёнка", "детей",
    }),
}

_TOKEN_RE = re.compile(r"[а-яёА-ЯЁa-zA-Z]+")

_sentiment_bundle: tuple[Any, Any] | None = None


def _ensure_sentiment_model() -> tuple[Any, Any]:
    global _sentiment_bundle
    if _sentiment_bundle is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            SENTIMENT_MODEL_NAME,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            SENTIMENT_MODEL_NAME,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
        model.eval()
        _sentiment_bundle = (tokenizer, model)
    return _sentiment_bundle


def unload_sentiment_model() -> None:
    global _sentiment_bundle
    _sentiment_bundle = None


def _tokenize(text: str) -> list[str]:
    return [m.lower() for m in _TOKEN_RE.findall(text)]


def _count_in(tokens: list[str], words: frozenset[str]) -> int:
    return sum(1 for t in tokens if t in words)


def _ratio(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return count / total


def _predict_sentiment(text: str) -> dict[str, float]:
    if not text.strip():
        return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
    import torch

    tokenizer, model = _ensure_sentiment_model()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0].tolist()
    return {SENTIMENT_LABELS[i]: float(probs[i]) for i in range(len(probs))}


def extract_features(text: str) -> dict[str, float]:
    tokens = _tokenize(text)
    n_tokens = len(tokens)

    sentiment = _predict_sentiment(text)

    features: dict[str, float] = {
        "sentiment_pos": sentiment.get("positive", 0.0),
        "sentiment_neg": sentiment.get("negative", 0.0),
        "sentiment_neu": sentiment.get("neutral", 0.0),
        "length_chars": float(len(text)),
        "length_tokens": float(n_tokens),
    }

    for group, words in PRONOUN_GROUPS.items():
        cnt = _count_in(tokens, words)
        features[f"pronoun_{group}_ratio"] = _ratio(cnt, n_tokens)

    for group, words in MARKER_WORDS.items():
        features[f"marker_{group}"] = float(_count_in(tokens, words))

    return features
