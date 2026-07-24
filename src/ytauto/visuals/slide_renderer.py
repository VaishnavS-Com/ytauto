"""Render 1920x1080 slides with Pillow — the reliable visual workhorse.

WHY PROGRAMMATIC SLIDES (and not AI images for everything)?
-----------------------------------------------------------
AI images are slow, sometimes wrong, and can't render text reliably.
A clean typographic slide is instant, deterministic, always on-brand, and
professional explainer channels use exactly this style. Strategy: slides
are the guaranteed baseline for every part; AI images are optional garnish
on top (visual_generator handles that). Reliable first, fancy second.

Pillow basics used here: Image.new (canvas), ImageDraw (drawing),
ImageFont (typography), and manual word-wrapping measured in PIXELS —
character-count wrapping breaks because 'W' is ~3x wider than 'i'.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ytauto.logging_setup import get_logger

log = get_logger(__name__)

SIZE = (1920, 1080)                 # YouTube full HD
BG = (18, 20, 28)                   # near-black blue — easy on the eyes
ACCENT = (86, 156, 255)             # channel accent color
TEXT = (235, 238, 245)
SUBTLE = (140, 148, 165)

# Windows / Linux / fallback — first hit wins. Font choice is channel
# identity; swap paths here when you brand the channel properly.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold (Windows)
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    log.warning("No TrueType font found — using PIL default (low quality)")
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Word-wrap by MEASURED pixel width, not character count."""
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_slide(
    out_path: Path,
    headline: str,
    body_text: str = "",
    kicker: str = "",
) -> Path:
    """Draw one slide: small kicker line, big headline, optional body text."""
    img = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(img)

    margin = 140
    max_width = SIZE[0] - 2 * margin
    y = 200

    # Accent bar — small touches make slides look designed, not generated.
    draw.rectangle([margin, y, margin + 90, y + 10], fill=ACCENT)
    y += 50

    if kicker:
        kicker_font = _load_font(40)
        draw.text((margin, y), kicker.upper(), font=kicker_font, fill=SUBTLE)
        y += 80

    headline_font = _load_font(88)
    for line in _wrap(draw, headline, headline_font, max_width)[:4]:
        draw.text((margin, y), line, font=headline_font, fill=TEXT)
        y += 108

    if body_text:
        y += 40
        body_font = _load_font(48)
        for line in _wrap(draw, body_text, body_font, max_width)[:5]:
            draw.text((margin, y), line, font=body_font, fill=SUBTLE)
            y += 64

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    log.info("Rendered slide %s", out_path.name)
    return out_path
