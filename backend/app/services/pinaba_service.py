from __future__ import annotations

import io
import logging
import textwrap
from pathlib import Path
from typing import Any

import qrcode
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("pinaba_service")

CANVAS_SIZE = 1080
BG = "#F1F5F9"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E2E8F0"
PRIMARY = "#5260FF"
DARK = "#0F172A"
SECONDARY = "#64748B"
MUTED = "#94A3B8"

LEVEL_COLOR: dict[str, str] = {
    "low": "#22C55E",
    "mid": "#F59E0B",
    "high": "#EF4444",
}

FONTS_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
MANROPE_VARIABLE = FONTS_DIR / "Manrope-VariableFont_wght.ttf"

FALLBACK_CANDIDATES: dict[str, tuple[Path, ...]] = {
    "regular": (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ),
    "bold": (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ),
}


def _load_font(
    weight: str, size: int
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if MANROPE_VARIABLE.is_file():
        try:
            font = ImageFont.truetype(str(MANROPE_VARIABLE), size=size)
            variation = b"Bold" if weight == "bold" else b"Regular"
            font.set_variation_by_name(variation)
            return font
        except (OSError, ValueError) as exc:
            logger.warning("Manrope variable font load failed: %s", exc)
    for path in FALLBACK_CANDIDATES.get(weight, ()):
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _make_qr(public_uuid: str, size_px: int = 180) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(f"/p/{public_uuid}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size_px, size_px), Image.Resampling.NEAREST)


def top_scales(
    scale_scores: list[dict[str, Any]], k: int = 6
) -> list[dict[str, Any]]:
    return sorted(
        scale_scores, key=lambda s: abs(float(s.get("value", 0)) - 50), reverse=True
    )[:k]


def top_takeaways(scale_scores: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    highs = sorted(
        [s for s in scale_scores if s.get("level") == "high"],
        key=lambda s: -float(s.get("value", 0)),
    )[:2]
    lows = sorted(
        [s for s in scale_scores if s.get("level") == "low"],
        key=lambda s: float(s.get("value", 0)),
    )[:1]
    for s in highs:
        items.append(
            f"Сильно проявлено: {s['scale_name']} ({float(s.get('value', 0)):.0f}/100)"
        )
    for s in lows:
        items.append(
            f"Точка роста: {s['scale_name']} ({float(s.get('value', 0)):.0f}/100)"
        )
    if not items:
        items.append("Профиль уравновешенный — продолжайте в том же ритме.")
    while len(items) < 3:
        items.append("Маленькие шаги стабильно лучше резких изменений.")
    return items[:3]


def _draw_text_right(
    draw: ImageDraw.ImageDraw,
    xy_right: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    draw.text((xy_right[0] - width, xy_right[1]), text, fill=fill, font=font)


def _wrap(text: str, width_chars: int) -> list[str]:
    return textwrap.wrap(text, width=width_chars) or [""]


def _draw_scale_row(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    width: int,
    scale: dict[str, Any],
    fonts: dict[str, ImageFont.ImageFont | ImageFont.FreeTypeFont],
) -> None:
    value = max(0.0, min(float(scale.get("value", 0)), 100.0))
    level = scale.get("level", "mid")
    color = LEVEL_COLOR.get(level, PRIMARY)

    dot_r = 12
    draw.ellipse(
        (x, y + 6, x + dot_r * 2, y + 6 + dot_r * 2),
        fill=color,
    )

    name_x = x + dot_r * 2 + 14
    draw.text((name_x, y), scale.get("scale_name", ""), fill=DARK, font=fonts["scale_name"])
    _draw_text_right(
        draw,
        (x + width, y),
        f"{value:.0f} / 100",
        fonts["scale_value"],
        color,
    )

    bar_y = y + 42
    bar_h = 14
    bx0 = name_x
    bx1 = x + width
    draw.rounded_rectangle(
        (bx0, bar_y, bx1, bar_y + bar_h),
        radius=7,
        fill="#E2E8F0",
    )
    fill_w = ((bx1 - bx0) * value) / 100.0
    if fill_w > 0:
        draw.rounded_rectangle(
            (bx0, bar_y, bx0 + fill_w, bar_y + bar_h),
            radius=7,
            fill=color,
        )


def generate_pinaba(profile_json: dict[str, Any], public_uuid: str) -> bytes:
    canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), BG)
    draw = ImageDraw.Draw(canvas)

    fonts = {
        "title": _load_font("bold", 56),
        "subtitle": _load_font("regular", 22),
        "section": _load_font("bold", 26),
        "scale_name": _load_font("bold", 22),
        "scale_value": _load_font("bold", 24),
        "body": _load_font("regular", 20),
        "small": _load_font("regular", 16),
        "footer": _load_font("regular", 14),
    }

    margin = 60
    content_w = CANVAS_SIZE - margin * 2

    qr_size = 180
    qr_img = _make_qr(public_uuid, size_px=qr_size)
    qr_x = CANVAS_SIZE - margin - qr_size
    qr_y = margin - 20
    canvas.paste(qr_img, (qr_x, qr_y))

    draw.text((margin, margin), "PsychoGraph", fill=PRIMARY, font=fonts["title"])
    draw.text(
        (margin, margin + 70),
        "Психологический профиль",
        fill=SECONDARY,
        font=fonts["subtitle"],
    )

    scales_section_y = margin + 130
    draw.text(
        (margin, scales_section_y),
        "Ключевые шкалы",
        fill=DARK,
        font=fonts["section"],
    )

    scales = top_scales(profile_json.get("scale_scores", []), k=6)
    row_h = 72
    row_y = scales_section_y + 50
    for idx, scale in enumerate(scales):
        _draw_scale_row(
            draw,
            x=margin,
            y=row_y + idx * row_h,
            width=content_w,
            scale=scale,
            fonts=fonts,
        )

    takeaways_y = row_y + len(scales) * row_h + 16
    draw.text(
        (margin, takeaways_y),
        "Главные выводы",
        fill=DARK,
        font=fonts["section"],
    )
    cursor_y = takeaways_y + 42
    for line in top_takeaways(profile_json.get("scale_scores", [])):
        wrapped = _wrap(line, width_chars=72)
        for wline in wrapped:
            draw.text(
                (margin, cursor_y),
                f"•  {wline}" if wline == wrapped[0] else f"    {wline}",
                fill=DARK,
                font=fonts["body"],
            )
            cursor_y += 28

    recs = list(profile_json.get("recommendations", []))[:2]
    if recs:
        cursor_y += 8
        draw.text(
            (margin, cursor_y),
            "Рекомендации",
            fill=DARK,
            font=fonts["section"],
        )
        cursor_y += 40
        for idx, rec in enumerate(recs, start=1):
            wrapped = _wrap(rec, width_chars=72)
            for wline in wrapped:
                prefix = f"{idx}.  " if wline == wrapped[0] else "    "
                draw.text(
                    (margin, cursor_y),
                    f"{prefix}{wline}",
                    fill=DARK,
                    font=fonts["body"],
                )
                cursor_y += 26

    footer_y = CANVAS_SIZE - margin - 20
    draw.text(
        (margin, footer_y),
        f"psychograph · /p/{public_uuid} · числа без текста",
        fill=MUTED,
        font=fonts["footer"],
    )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
