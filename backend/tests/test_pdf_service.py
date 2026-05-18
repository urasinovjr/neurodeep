from __future__ import annotations

from typing import Any

import pytest

from app.services.pdf_service import (
    PdfService,
    build_bar_svg,
    build_radar_svg,
    build_wheel_svg,
)


def _sample_profile() -> dict[str, Any]:
    return {
        "scale_scores": [
            {
                "scale_id": 1,
                "scale_name": "Тревожность",
                "value": 78.0,
                "level": "high",
                "fragment": "Высокий уровень тревожности (78/100).",
            },
            {
                "scale_id": 2,
                "scale_name": "Перфекционизм",
                "value": 45.0,
                "level": "mid",
                "fragment": "Средний уровень перфекционизма (45/100).",
            },
            {
                "scale_id": 3,
                "scale_name": "Соматизация",
                "value": 22.0,
                "level": "low",
                "fragment": "Низкий уровень соматизации (22/100).",
            },
        ],
        "text_interpretation": (
            "Профиль показывает высокий уровень тревожности 78, "
            "средний перфекционизм 45 и низкую соматизацию 22."
        ),
        "recommendations": [
            "Обратите внимание на тревожность — короткие практики дыхания снижают пик.",
            "Перфекционизм — попробуйте принцип \"достаточно хорошо\" для рутины.",
        ],
        "wheel_balance": {
            "emotions": 78.0,
            "thinking": 45.0,
            "body": 22.0,
            "relationships": 0.0,
            "meaning": 0.0,
        },
    }


def test_build_radar_svg_contains_scale_names() -> None:
    profile = _sample_profile()
    svg = build_radar_svg(profile["scale_scores"])
    assert svg.startswith("<svg")
    assert "Тревожность" in svg
    assert "Перфекционизм" in svg
    assert "Соматизация" in svg
    assert "<polygon" in svg


def test_build_radar_svg_returns_empty_when_fewer_than_three_scales() -> None:
    svg = build_radar_svg([
        {"scale_name": "A", "value": 50, "level": "mid"},
        {"scale_name": "B", "value": 50, "level": "mid"},
    ])
    assert svg == ""


def test_build_bar_svg_clamps_value_and_uses_level_color() -> None:
    svg = build_bar_svg({"value": 78.0, "level": "high"})
    assert svg.startswith("<svg")
    assert "#EF4444" in svg
    over = build_bar_svg({"value": 250, "level": "high"})
    assert "<svg" in over


def test_build_wheel_svg_contains_all_5_domains() -> None:
    svg = build_wheel_svg(_sample_profile()["wheel_balance"])
    for label in ("Эмоции", "Мышление", "Тело", "Отношения", "Смыслы"):
        assert label in svg


def test_render_html_contains_title_scales_and_text() -> None:
    service = PdfService()
    html = service.render_html(_sample_profile(), title="Психологический профиль")
    assert "Психологический профиль" in html
    assert "Тревожность" in html
    assert "Перфекционизм" in html
    assert "78" in html
    assert "45" in html
    assert "22" in html
    assert "высокий" in html
    assert "средний" in html
    assert "низкий" in html
    assert "Рекомендации" in html
    assert "<svg" in html


def test_render_html_handles_empty_recommendations_and_wheel() -> None:
    service = PdfService()
    profile = _sample_profile()
    profile["recommendations"] = []
    profile["wheel_balance"] = {}
    html = service.render_html(profile)
    assert "Тревожность" in html
    assert "Рекомендации" not in html


def _weasyprint_available() -> bool:
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        return False
    try:
        HTML(string="<p>x</p>").write_pdf()
    except Exception:
        return False
    return True


pytestmark_pdf = pytest.mark.skipif(
    not _weasyprint_available(),
    reason="WeasyPrint native libs not available on this host",
)


@pytestmark_pdf
def test_generate_pdf_returns_bytes_with_pdf_magic() -> None:
    service = PdfService()
    pdf = service.generate_pdf(_sample_profile())
    assert isinstance(pdf, bytes)
    assert pdf[:5] == b"%PDF-"


@pytestmark_pdf
def test_generate_pdf_under_500_kb() -> None:
    service = PdfService()
    pdf = service.generate_pdf(_sample_profile())
    assert len(pdf) < 500 * 1024


@pytestmark_pdf
def test_generate_pdf_contains_expected_scale_values_via_pdftotext() -> None:
    pypdf = pytest.importorskip("pypdf")
    service = PdfService()
    pdf = service.generate_pdf(_sample_profile())
    import io

    reader = pypdf.PdfReader(io.BytesIO(pdf))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Тревожность" in text
    assert "Перфекционизм" in text
    assert "Соматизация" in text
    assert "78" in text
    assert "45" in text
    assert "22" in text
