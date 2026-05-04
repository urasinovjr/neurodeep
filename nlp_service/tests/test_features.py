import os
import time
from pathlib import Path

import pytest

from app.features import (
    MARKER_WORDS,
    PRONOUN_GROUPS,
    _count_in,
    _ratio,
    _tokenize,
    extract_features,
)


def _sentiment_model_available() -> bool:
    try:
        import transformers  # noqa: F401
    except ImportError:
        return False
    cache_dir = os.environ.get("MODEL_CACHE_DIR", "/opt/hf-cache")
    expected = Path(cache_dir) / "hub" / "models--seara--rubert-tiny2-russian-sentiment"
    return expected.exists()


needs_model = pytest.mark.skipif(
    not _sentiment_model_available(),
    reason="Sentiment model (seara/rubert-tiny2-russian-sentiment) not cached; will be downloaded on first run inside docker",
)


EXPECTED_KEYS = {
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
}


def test_tokenize_lowercases_and_splits():
    tokens = _tokenize("Я думаю, что должен быть идеальным")
    assert tokens == ["я", "думаю", "что", "должен", "быть", "идеальным"]


def test_tokenize_skips_punctuation_and_numbers():
    tokens = _tokenize("Привет!!! 123 как дела?")
    assert tokens == ["привет", "как", "дела"]


def test_tokenize_handles_empty():
    assert _tokenize("") == []


def test_count_in_basic():
    tokens = ["я", "должен", "всегда"]
    assert _count_in(tokens, MARKER_WORDS["should"]) == 1
    assert _count_in(tokens, MARKER_WORDS["always"]) == 1
    assert _count_in(tokens, MARKER_WORDS["never"]) == 0


def test_ratio_zero_total_returns_zero():
    assert _ratio(0, 0) == 0.0
    assert _ratio(5, 0) == 0.0


def test_ratio_normal():
    assert _ratio(2, 4) == 0.5


def test_pronoun_groups_disjoint():
    seen: set[str] = set()
    for words in PRONOUN_GROUPS.values():
        for w in words:
            assert w not in seen, f"pronoun '{w}' duplicated across groups"
            seen.add(w)


@needs_model
def test_extract_features_returns_all_expected_keys():
    result = extract_features("Я думаю, что должен быть идеальным")
    assert set(result.keys()) == EXPECTED_KEYS
    for key, value in result.items():
        assert isinstance(value, float), f"{key} is {type(value).__name__}, expected float"


@needs_model
def test_extract_features_marker_should_on_acceptance_phrase():
    result = extract_features("Я думаю, что должен быть идеальным")
    assert result["marker_should"] >= 1


@needs_model
def test_extract_features_sentiment_neg_on_negative_text():
    result = extract_features("Я ненавижу всё это, мне очень плохо")
    assert result["sentiment_neg"] > 0.3


@needs_model
def test_extract_features_lengths():
    result = extract_features("Привет")
    assert result["length_chars"] == 6.0
    assert result["length_tokens"] == 1.0


@needs_model
def test_extract_features_empty_text_no_crash():
    result = extract_features("")
    assert result["length_chars"] == 0.0
    assert result["length_tokens"] == 0.0
    assert result["pronoun_i_ratio"] == 0.0
    assert result["pronoun_we_ratio"] == 0.0
    assert result["pronoun_you_ratio"] == 0.0


@needs_model
def test_extract_features_pronouns():
    result = extract_features("Я и мы вместе")
    assert result["pronoun_i_ratio"] > 0
    assert result["pronoun_we_ratio"] > 0
    assert result["pronoun_you_ratio"] == 0.0


@needs_model
def test_extract_features_body_part_marker():
    result = extract_features("У меня болит голова")
    assert result["marker_body_part"] >= 2


@needs_model
def test_extract_features_family_and_always_markers():
    result = extract_features("родители всегда правы")
    assert result["marker_family"] >= 1
    assert result["marker_always"] >= 1


@needs_model
def test_extract_features_warm_call_under_100ms():
    extract_features("разогрев")
    timings: list[float] = []
    for _ in range(5):
        started = time.perf_counter()
        extract_features("Я думаю, что должен быть идеальным сегодня и завтра")
        timings.append((time.perf_counter() - started) * 1000.0)
    assert max(timings) < 100.0, f"max warm-call timing {max(timings):.1f}ms exceeded 100ms; all={timings}"
