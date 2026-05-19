from __future__ import annotations

import io
from typing import Any

import pytest
from PIL import Image

from app.services.pinaba_service import (
    CANVAS_SIZE,
    _make_qr,
    generate_pinaba,
    top_scales,
    top_takeaways,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _sample_profile() -> dict[str, Any]:
    return {
        "scale_scores": [
            {
                "scale_id": 1,
                "scale_name": "Тревожность",
                "value": 78.0,
                "level": "high",
                "fragment": "Высокая тревожность 78/100.",
            },
            {
                "scale_id": 2,
                "scale_name": "Перфекционизм",
                "value": 45.0,
                "level": "mid",
                "fragment": "Средний перфекционизм 45/100.",
            },
            {
                "scale_id": 3,
                "scale_name": "Соматизация",
                "value": 22.0,
                "level": "low",
                "fragment": "Низкая соматизация 22/100.",
            },
            {
                "scale_id": 4,
                "scale_name": "Эмоциональная регуляция",
                "value": 60.0,
                "level": "mid",
                "fragment": "Средняя регуляция 60/100.",
            },
            {
                "scale_id": 5,
                "scale_name": "Когнитивный контроль",
                "value": 85.0,
                "level": "high",
                "fragment": "Высокий контроль 85/100.",
            },
            {
                "scale_id": 6,
                "scale_name": "Социальная коммуникация",
                "value": 30.0,
                "level": "low",
                "fragment": "Низкая коммуникация 30/100.",
            },
            {
                "scale_id": 7,
                "scale_name": "Резерв",
                "value": 51.0,
                "level": "mid",
                "fragment": "Без выраженных проявлений.",
            },
        ],
        "text_interpretation": "Полная интерпретация…",
        "recommendations": [
            "Обратите внимание на тревожность — короткие практики дыхания снижают пик.",
            "Перфекционизм — попробуйте принцип «достаточно хорошо» для рутины.",
        ],
        "wheel_balance": {
            "emotions": 70.0,
            "thinking": 65.0,
            "body": 22.0,
            "relationships": 30.0,
            "meaning": 50.0,
        },
    }


def test_top_scales_picks_strongest_deviation_from_50() -> None:
    scales = _sample_profile()["scale_scores"]
    top = top_scales(scales, k=3)
    names = [s["scale_name"] for s in top]
    assert "Когнитивный контроль" in names
    assert "Тревожность" in names
    assert "Соматизация" in names
    assert "Резерв" not in names


def test_top_scales_respects_k_limit() -> None:
    assert len(top_scales(_sample_profile()["scale_scores"], k=4)) == 4
    assert len(top_scales(_sample_profile()["scale_scores"], k=10)) == 7


def test_top_takeaways_returns_exactly_three_items() -> None:
    items = top_takeaways(_sample_profile()["scale_scores"])
    assert len(items) == 3
    joined = " ".join(items)
    assert "Сильно проявлено" in joined or "Точка роста" in joined


def test_top_takeaways_pads_with_neutral_when_balanced() -> None:
    items = top_takeaways(
        [
            {"scale_name": "A", "value": 50, "level": "mid"},
            {"scale_name": "B", "value": 50, "level": "mid"},
        ]
    )
    assert len(items) == 3
    assert any("уравновешенный" in item or "Маленькие шаги" in item for item in items)


def test_make_qr_returns_image_with_expected_size() -> None:
    img = _make_qr("abcd-1234", size_px=180)
    assert img.size == (180, 180)
    assert img.mode == "RGB"


def test_generate_pinaba_returns_png_bytes() -> None:
    pdf = generate_pinaba(_sample_profile(), "test-uuid-1234")
    assert isinstance(pdf, bytes)
    assert pdf.startswith(PNG_MAGIC)


def test_generate_pinaba_format_and_size() -> None:
    data = generate_pinaba(_sample_profile(), "abcd")
    img = Image.open(io.BytesIO(data))
    assert img.format == "PNG"
    assert img.mode == "RGB"
    assert img.size == (CANVAS_SIZE, CANVAS_SIZE)


def test_generate_pinaba_under_200_kb() -> None:
    data = generate_pinaba(_sample_profile(), "abcd")
    assert len(data) < 200 * 1024


def test_generate_pinaba_does_not_render_pii_fields() -> None:
    profile = _sample_profile()
    profile["user_email"] = "secret@example.com"
    profile["user_first_name"] = "Иван"
    profile["user_last_name"] = "Иванов"
    data = generate_pinaba(profile, "abcd")
    assert b"secret@example.com" not in data
    assert "Иванов".encode() not in data


def test_generate_pinaba_handles_no_recommendations() -> None:
    profile = _sample_profile()
    profile["recommendations"] = []
    data = generate_pinaba(profile, "abcd")
    img = Image.open(io.BytesIO(data))
    assert img.size == (CANVAS_SIZE, CANVAS_SIZE)


def test_generate_pinaba_handles_short_scale_list() -> None:
    profile = {
        "scale_scores": [
            {"scale_id": 1, "scale_name": "A", "value": 80.0, "level": "high"},
            {"scale_id": 2, "scale_name": "B", "value": 20.0, "level": "low"},
        ],
        "recommendations": ["Совет."],
        "text_interpretation": "",
        "wheel_balance": {},
    }
    data = generate_pinaba(profile, "abcd")
    assert data.startswith(PNG_MAGIC)
    img = Image.open(io.BytesIO(data))
    assert img.size == (CANVAS_SIZE, CANVAS_SIZE)


@pytest.mark.parametrize("uuid_input", ["a", "abcd-1234", "uuid-" + "x" * 64])
def test_generate_pinaba_qr_uuid_lengths_dont_break(uuid_input: str) -> None:
    data = generate_pinaba(_sample_profile(), uuid_input)
    assert data.startswith(PNG_MAGIC)
