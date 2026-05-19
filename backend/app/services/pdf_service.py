from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("pdf_service")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PDF_SUBDIR = "pdf"
PDF_TEMPLATE = f"{PDF_SUBDIR}/profile_pdf.html"

LEVEL_COLOR = {
    "low": "#22C55E",
    "mid": "#F59E0B",
    "high": "#EF4444",
}
LEVEL_LABEL = {
    "low": "низкий",
    "mid": "средний",
    "high": "высокий",
}

PRIMARY = "#5260FF"
GRID = "#CBD5E1"
AXIS_LABEL = "#475569"
RADAR_FILL = "rgba(82, 96, 255, 0.25)"

DOMAIN_LABELS: dict[str, str] = {
    "emotions": "Эмоции",
    "thinking": "Мышление",
    "body": "Тело",
    "relationships": "Отношения",
    "meaning": "Смыслы",
}

DOMAIN_COLORS: tuple[str, ...] = (
    "#5260FF",
    "#8B5CF6",
    "#EC4899",
    "#22C55E",
    "#F59E0B",
)


def _format_value(value: float) -> str:
    return f"{value:.0f}"


def _polar_to_xy(cx: float, cy: float, r: float, angle_rad: float) -> tuple[float, float]:
    return cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)


def build_radar_svg(
    scales: Sequence[dict[str, Any]],
    size: int = 360,
) -> str:
    if len(scales) < 3:
        return ""
    cx = cy = size / 2
    r_max = size * 0.36
    n = len(scales)
    rings = (25, 50, 75, 100)

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="100%" height="auto" role="img" aria-label="Радар-диаграмма шкал">'
    )

    for percent in rings:
        rr = r_max * (percent / 100)
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" '
            f'fill="none" stroke="{GRID}" stroke-width="0.6" />'
        )

    axes_points: list[tuple[float, float]] = []
    label_positions: list[tuple[float, float, str, str]] = []
    for idx, item in enumerate(scales):
        angle = -math.pi / 2 + (2 * math.pi * idx) / n
        ax, ay = _polar_to_xy(cx, cy, r_max, angle)
        axes_points.append((ax, ay))
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" '
            f'stroke="{GRID}" stroke-width="0.6" />'
        )
        lx, ly = _polar_to_xy(cx, cy, r_max + 18, angle)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        label_positions.append((lx, ly, item.get("scale_name", ""), anchor))

    polygon_points: list[str] = []
    dot_points: list[tuple[float, float, str]] = []
    for idx, item in enumerate(scales):
        value = float(item.get("value", 0))
        ratio = max(0.0, min(value, 100.0)) / 100.0
        angle = -math.pi / 2 + (2 * math.pi * idx) / n
        px, py = _polar_to_xy(cx, cy, r_max * ratio, angle)
        polygon_points.append(f"{px:.1f},{py:.1f}")
        level = item.get("level", "mid")
        dot_points.append((px, py, LEVEL_COLOR.get(level, PRIMARY)))

    parts.append(
        f'<polygon points="{" ".join(polygon_points)}" '
        f'fill="{RADAR_FILL}" stroke="{PRIMARY}" stroke-width="1.8" stroke-linejoin="round" />'
    )

    for px, py, color in dot_points:
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" '
            f'fill="{color}" stroke="white" stroke-width="1" />'
        )

    for lx, ly, name, anchor in label_positions:
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" fill="{AXIS_LABEL}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">{_escape_xml(name)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def build_bar_svg(scale: dict[str, Any], width: int = 480, height: int = 32) -> str:
    value = max(0.0, min(float(scale.get("value", 0)), 100.0))
    level = scale.get("level", "mid")
    color = LEVEL_COLOR.get(level, PRIMARY)
    bar_w = width - 8
    fill_w = (bar_w * value) / 100.0
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="auto" role="img" aria-label="Уровень шкалы">'
        f'<rect x="4" y="{height / 2 - 6:.1f}" width="{bar_w}" height="12" '
        f'rx="6" ry="6" fill="#E2E8F0" />'
        f'<rect x="4" y="{height / 2 - 6:.1f}" width="{fill_w:.1f}" height="12" '
        f'rx="6" ry="6" fill="{color}" />'
        f"</svg>"
    )


def build_wheel_svg(
    wheel_balance: dict[str, float],
    size: int = 320,
) -> str:
    cx = cy = size / 2
    r = size * 0.36
    domains = list(DOMAIN_LABELS.keys())
    n = len(domains)
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="100%" height="auto" role="img" aria-label="Колесо баланса">'
    )

    for percent in (25, 50, 75, 100):
        rr = r * (percent / 100)
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" '
            f'fill="none" stroke="{GRID}" stroke-width="0.6" />'
        )

    polygon_points: list[str] = []
    for idx, domain in enumerate(domains):
        value = max(0.0, min(float(wheel_balance.get(domain, 0.0)), 100.0))
        ratio = value / 100.0
        angle = -math.pi / 2 + (2 * math.pi * idx) / n
        ax, ay = _polar_to_xy(cx, cy, r, angle)
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" '
            f'stroke="{GRID}" stroke-width="0.6" />'
        )
        px, py = _polar_to_xy(cx, cy, r * ratio, angle)
        polygon_points.append(f"{px:.1f},{py:.1f}")

    parts.append(
        f'<polygon points="{" ".join(polygon_points)}" '
        f'fill="rgba(82, 96, 255, 0.20)" stroke="{PRIMARY}" stroke-width="1.6" stroke-linejoin="round" />'
    )

    for idx, domain in enumerate(domains):
        value = max(0.0, min(float(wheel_balance.get(domain, 0.0)), 100.0))
        ratio = value / 100.0
        angle = -math.pi / 2 + (2 * math.pi * idx) / n
        px, py = _polar_to_xy(cx, cy, r * ratio, angle)
        color = DOMAIN_COLORS[idx % len(DOMAIN_COLORS)]
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{color}" stroke="white" stroke-width="1" />'
        )
        lx, ly = _polar_to_xy(cx, cy, r + 18, angle)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        label = f"{DOMAIN_LABELS[domain]} · {value:.0f}"
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" fill="{AXIS_LABEL}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">{_escape_xml(label)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class PdfService:
    def __init__(self, templates_dir: Path | None = None) -> None:
        root = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(root)),
            autoescape=select_autoescape(enabled_extensions=("html",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["fmt"] = _format_value
        self.env.filters["level_label"] = lambda level: LEVEL_LABEL.get(level, level)
        self.env.filters["level_color"] = lambda level: LEVEL_COLOR.get(level, PRIMARY)

    def render_html(
        self,
        profile_json: dict[str, Any],
        title: str = "Психологический профиль",
    ) -> str:
        scales = list(profile_json.get("scale_scores", []))
        wheel = profile_json.get("wheel_balance", {}) or {}
        radar_svg = build_radar_svg(scales)
        wheel_svg = build_wheel_svg(wheel) if wheel else ""
        bar_svgs = [build_bar_svg(scale) for scale in scales]
        template = self.env.get_template(PDF_TEMPLATE)
        return template.render(
            title=title,
            scales=scales,
            bar_svgs=bar_svgs,
            radar_svg=radar_svg,
            wheel_svg=wheel_svg,
            text_interpretation=profile_json.get("text_interpretation", ""),
            recommendations=profile_json.get("recommendations", []),
            domain_labels=DOMAIN_LABELS,
        )

    def generate_pdf(
        self,
        profile_json: dict[str, Any],
        title: str = "Психологический профиль",
    ) -> bytes:
        from weasyprint import HTML

        html = self.render_html(profile_json, title=title)
        pdf_bytes = HTML(string=html).write_pdf()
        if pdf_bytes is None:
            raise RuntimeError("WeasyPrint returned no PDF bytes")
        return pdf_bytes
