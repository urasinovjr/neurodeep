import pytest

from app.services.profile_service import ProfileRenderService, level_from_value


def _items(*specs: tuple[int, str, float]) -> list[dict]:
    return [
        {
            "scale_id": sid,
            "scale_name": name,
            "value": value,
            "confidence": 0.5,
        }
        for sid, name, value in specs
    ]


def test_level_from_value_thresholds() -> None:
    assert level_from_value(0) == "low"
    assert level_from_value(33.99) == "low"
    assert level_from_value(34) == "mid"
    assert level_from_value(66.99) == "mid"
    assert level_from_value(67) == "high"
    assert level_from_value(100) == "high"


def test_master_render_contains_value_78_and_scale_name() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=1,
        methodology_name="КПТ",
        scales=_items((1, "Перфекционизм", 78.0)),
    )
    assert "78" in text
    assert "Перфекционизм" in text
    assert "КПТ" in text
    assert "высокий" in text.lower()


def test_master_render_uses_default_when_override_missing() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=999,
        methodology_name="Несуществующая",
        scales=_items((42, "Случайная шкала", 50.0)),
    )
    assert "50" in text
    assert "средний" in text.lower()
    assert "Случайная шкала" in text


def test_master_render_picks_override_when_present() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=2,
        methodology_name="Гештальт",
        scales=_items((1, "Перфекционизм", 80.0)),
    )
    assert "80" in text
    assert "выраженный перфекционизм" in text.lower()


def test_master_render_handles_multiple_scales_in_different_levels() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=1,
        methodology_name="КПТ",
        scales=_items(
            (10, "Тревожность", 78.0),
            (11, "Импульсивность", 50.0),
            (12, "Самокритика", 20.0),
        ),
    )
    assert "78" in text
    assert "50" in text
    assert "20" in text
    assert "Тревожность" in text
    assert "Импульсивность" in text
    assert "Самокритика" in text
    assert "высокий" in text.lower()
    assert "средний" in text.lower()
    assert "низкий" in text.lower()


def test_master_render_includes_recommendations_block() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=1,
        methodology_name="КПТ",
        scales=_items(
            (10, "Тревожность", 78.0),
            (11, "Импульсивность", 20.0),
        ),
    )
    assert "Общие рекомендации" in text
    assert "Тревожность" in text
    assert "Импульсивность" in text


def test_master_render_balanced_profile_recommendations() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=1,
        methodology_name="КПТ",
        scales=_items((10, "A", 50.0), (11, "B", 50.0)),
    )
    assert "уравновешенный" in text.lower()


def test_master_render_empty_scales_does_not_crash() -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=1,
        methodology_name="КПТ",
        scales=[],
    )
    assert "КПТ" in text


@pytest.mark.parametrize(
    "value,level_expected",
    [(10, "низкий"), (50, "средний"), (90, "высокий")],
)
def test_master_render_level_label_matches_value(
    value: float, level_expected: str
) -> None:
    service = ProfileRenderService()
    text = service.render_master(
        methodology_id=1,
        methodology_name="КПТ",
        scales=_items((1, "Шкала", value)),
    )
    assert level_expected in text.lower()
