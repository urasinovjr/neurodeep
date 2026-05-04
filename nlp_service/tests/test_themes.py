import os
from pathlib import Path

import pytest

from app.themes import (
    THEME_KEYWORDS,
    THEME_REFERENCES,
    THEME_TAGS,
    detect_themes,
)


def _rubert_cached() -> bool:
    try:
        import transformers  # noqa: F401
    except ImportError:
        return False
    cache_dir = os.environ.get("MODEL_CACHE_DIR", "/opt/hf-cache")
    expected = Path(cache_dir) / "hub" / "models--DeepPavlov--rubert-base-cased"
    return expected.exists()


needs_rubert = pytest.mark.skipif(
    not _rubert_cached(),
    reason="ruBERT model not cached; will be downloaded on first run inside docker",
)


def test_theme_tags_unique_and_six():
    assert len(THEME_TAGS) == 6
    assert len(set(THEME_TAGS)) == 6


def test_theme_keywords_keys_match_tags():
    assert set(THEME_KEYWORDS.keys()) == set(THEME_TAGS)
    for tag in THEME_TAGS:
        assert len(THEME_KEYWORDS[tag]) > 0
        for word in THEME_KEYWORDS[tag]:
            assert word == word.lower(), f"keyword '{word}' should be lowercase"


def test_theme_references_keys_match_tags():
    assert set(THEME_REFERENCES.keys()) == set(THEME_TAGS)
    for tag in THEME_TAGS:
        assert len(THEME_REFERENCES[tag]) >= 3
        for sentence in THEME_REFERENCES[tag]:
            assert sentence.strip(), f"empty reference in tag '{tag}'"


def test_theme_reference_phrases_are_distinct_per_tag():
    for tag in THEME_TAGS:
        sentences = THEME_REFERENCES[tag]
        assert len(set(sentences)) == len(sentences), f"duplicate ref in '{tag}'"


@needs_rubert
def test_detect_themes_acceptance_step1_cbt_top():
    result = detect_themes("я часто думаю что должен")
    assert len(result) > 0
    assert result[0]["tag"] == "cbt"


@needs_rubert
def test_detect_themes_acceptance_step2_psychosomatic_top():
    result = detect_themes("болит голова и тяжесть в груди")
    assert len(result) > 0
    assert result[0]["tag"] == "psychosomatic"


@needs_rubert
def test_detect_themes_empty_text_returns_empty_list():
    assert detect_themes("") == []
    assert detect_themes("   ") == []


@needs_rubert
def test_detect_themes_scores_in_range_and_sorted():
    result = detect_themes("Мои родители всегда были строгими и я должен был соответствовать")
    assert len(result) > 0
    for item in result:
        assert 0.0 <= item["score"] <= 1.0
        assert item["score"] > 0.3
    scores = [item["score"] for item in result]
    assert scores == sorted(scores, reverse=True)


@needs_rubert
def test_detect_themes_family_keyword_lifts_family_theme():
    result = detect_themes("Мои родители и моя мама всегда были строгими")
    tags = [item["tag"] for item in result]
    assert "family" in tags
    assert tags.index("family") <= 2


@needs_rubert
def test_detect_themes_only_returns_above_threshold():
    result = detect_themes("сегодня солнечно и тепло")
    for item in result:
        assert item["score"] > 0.3
