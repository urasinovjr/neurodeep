import logging
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from app.db.repositories import (
    MethodologyRepository,
    ScaleRepository,
    ScaleScoreRepository,
    SurveyRepository,
    SurveySessionRepository,
)

logger = logging.getLogger("profile_service")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PROFILES_SUBDIR = "profiles"

LOW_THRESHOLD = Decimal("34")
HIGH_THRESHOLD = Decimal("67")

ScaleScoreItem = dict[str, Any]

WHEEL_DOMAINS: tuple[str, ...] = (
    "emotions",
    "thinking",
    "body",
    "relationships",
    "meaning",
)
DEFAULT_DOMAIN = "emotions"
DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "emotions": (
        "тревож",
        "стресс",
        "эмоц",
        "грусть",
        "радост",
        "страх",
        "гнев",
        "настроен",
    ),
    "thinking": (
        "мышлен",
        "размышл",
        "рассужд",
        "перфекц",
        "когн",
        "рацион",
        "обсесс",
        "сомнен",
        "внимани",
        "контрол",
    ),
    "body": (
        "тело",
        "сомат",
        "болезн",
        "усталост",
        "сон",
        "энерг",
        "напряж",
        "здоров",
    ),
    "relationships": (
        "близост",
        "отношен",
        "семь",
        "довер",
        "конфликт",
        "связ",
        "коммуник",
        "социальн",
    ),
    "meaning": (
        "смысл",
        "цел",
        "ценност",
        "верован",
        "духовн",
        "осознан",
        "идентичност",
        "миссия",
        "призван",
    ),
}


def level_from_value(value: float | Decimal) -> str:
    v = Decimal(str(value))
    if v < LOW_THRESHOLD:
        return "low"
    if v < HIGH_THRESHOLD:
        return "mid"
    return "high"


def assign_domain(scale_name: str) -> str:
    name = scale_name.lower()
    for domain in WHEEL_DOMAINS:
        for keyword in DOMAIN_KEYWORDS[domain]:
            if keyword in name:
                return domain
    return DEFAULT_DOMAIN


def compute_wheel_balance(scales: list[ScaleScoreItem]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {d: [] for d in WHEEL_DOMAINS}
    for item in scales:
        domain = assign_domain(item["scale_name"])
        buckets[domain].append(float(item["value"]))
    return {
        d: round(sum(values) / len(values), 2) if values else 0.0
        for d, values in buckets.items()
    }


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
            self.render_fragment(methodology_id, item) for item in scales
        ]
        recommendations = self.build_recommendations(scales)
        master = self.env.get_template(f"{PROFILES_SUBDIR}/master.j2")
        return master.render(
            methodology_name=methodology_name,
            fragments=fragments,
            recommendations=recommendations,
        )

    def render_fragment(
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

    def build_recommendations(
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


class ProfileService:
    def __init__(
        self,
        session_repo: SurveySessionRepository,
        survey_repo: SurveyRepository,
        methodology_repo: MethodologyRepository,
        scale_repo: ScaleRepository,
        scale_score_repo: ScaleScoreRepository,
        render_service: ProfileRenderService | None = None,
    ) -> None:
        self.session_repo = session_repo
        self.survey_repo = survey_repo
        self.methodology_repo = methodology_repo
        self.scale_repo = scale_repo
        self.scale_score_repo = scale_score_repo
        self.render_service = render_service or ProfileRenderService()

    async def build_profile_json(
        self, session_id: uuid.UUID
    ) -> dict[str, Any] | None:
        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            return None
        survey = await self.survey_repo.get_by_id(session.survey_id)
        if survey is None:
            return None
        methodology = await self.methodology_repo.get_by_id(survey.methodology_id)
        if methodology is None:
            return None
        scores = await self.scale_score_repo.get_by_session(session_id)
        if not scores:
            return None

        scale_ids = [s.scale_id for s in scores]
        scale_rows = await self.scale_repo.get_by_ids(scale_ids)
        scale_name_by_id = {s.id: s.name for s in scale_rows}

        items: list[ScaleScoreItem] = [
            {
                "scale_id": s.scale_id,
                "scale_name": scale_name_by_id.get(s.scale_id, f"Шкала {s.scale_id}"),
                "value": float(s.value),
                "confidence": float(s.confidence),
            }
            for s in scores
        ]

        text_interpretation = self.render_service.render_master(
            methodology_id=methodology.id,
            methodology_name=methodology.name,
            scales=items,
        )
        recommendations = self.render_service.build_recommendations(items)
        wheel_balance = compute_wheel_balance(items)
        scale_scores = [
            {
                "scale_id": item["scale_id"],
                "scale_name": item["scale_name"],
                "value": item["value"],
                "level": level_from_value(item["value"]),
                "fragment": self.render_service.render_fragment(methodology.id, item),
            }
            for item in items
        ]
        return {
            "scale_scores": scale_scores,
            "text_interpretation": text_interpretation,
            "recommendations": recommendations,
            "wheel_balance": wheel_balance,
        }
