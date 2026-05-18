import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = logging.getLogger("profile_service")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PROFILES_SUBDIR = "profiles"

LOW_THRESHOLD = Decimal("34")
HIGH_THRESHOLD = Decimal("67")

ScaleScoreItem = dict[str, Any]


def level_from_value(value: float | Decimal) -> str:
    v = Decimal(str(value))
    if v < LOW_THRESHOLD:
        return "low"
    if v < HIGH_THRESHOLD:
        return "mid"
    return "high"


class ProfileRenderService:
    def __init__(self, templates_dir: Path | None = None) -> None:
        root = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(root)),
            autoescape=select_autoescape(disabled_extensions=("j2",), default=False),
            trim_blocks=False,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

    def render_master(
        self,
        methodology_id: int,
        methodology_name: str,
        scales: list[ScaleScoreItem],
    ) -> str:
        fragments = [
            self._render_fragment(methodology_id, item) for item in scales
        ]
        recommendations = self._build_recommendations(scales)
        master = self.env.get_template(f"{PROFILES_SUBDIR}/master.j2")
        return master.render(
            methodology_name=methodology_name,
            fragments=fragments,
            recommendations=recommendations,
        )

    def _render_fragment(
        self, methodology_id: int, item: ScaleScoreItem
    ) -> str:
        level = level_from_value(item["value"])
        candidates = [
            f"{PROFILES_SUBDIR}/{methodology_id}/{item['scale_id']}_{level}.j2",
            f"{PROFILES_SUBDIR}/_default/{level}.j2",
        ]
        for path in candidates:
            try:
                template = self.env.get_template(path)
            except TemplateNotFound:
                continue
            return template.render(
                scale_id=item["scale_id"],
                scale_name=item["scale_name"],
                value=float(item["value"]),
                confidence=float(item.get("confidence", 0.0)),
                level=level,
            )
        logger.warning(
            "profile fragment missing: methodology_id=%s scale_id=%s level=%s",
            methodology_id,
            item["scale_id"],
            level,
        )
        return ""

    def _build_recommendations(
        self, scales: list[ScaleScoreItem]
    ) -> list[str]:
        recs: list[str] = []
        highs = [s for s in scales if level_from_value(s["value"]) == "high"]
        lows = [s for s in scales if level_from_value(s["value"]) == "low"]
        if highs:
            names = ", ".join(s["scale_name"] for s in highs[:3])
            recs.append(
                f"Обратите внимание на сильно выраженные шкалы ({names}) — там полезнее всего работать с гибкостью."
            )
        if lows:
            names = ", ".join(s["scale_name"] for s in lows[:3])
            recs.append(
                f"Слабо выраженные шкалы ({names}) — точки роста, где маленькие шаги дадут видимый эффект."
            )
        if not recs:
            recs.append(
                "Профиль уравновешенный — попробуйте ставить цели исходя из контекста, а не «улучшения» отдельных шкал."
            )
        return recs
