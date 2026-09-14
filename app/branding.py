import io
import logging
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .config import CHANNEL_LOGO_URL, CHANNEL_NAME

logger = logging.getLogger(__name__)

# Matches the channel's actual logo (dark warm charcoal card, red circle,
# cream-white text) so every generated graphic - intro card, name tags,
# thumbnails - reads as the same brand instead of a generic placeholder look.
BACKGROUND_COLOR = (26, 23, 21)
ACCENT_COLOR = (196, 30, 42)
TEXT_COLOR = (240, 235, 220)

_BACKGROUND_COLOR = BACKGROUND_COLOR
_ACCENT_COLOR = ACCENT_COLOR

INTRO_NARRATION = f"{CHANNEL_NAME}, tu informador de confianza."

# YouTube avatar CDN URLs take a "=sNNN-..." size suffix; try a bigger version
# of the logo first (better quality once scaled up to full video frame size),
# falling back to the exact URL given if that request fails for any reason.
_LOGO_URL_CANDIDATES = (
    [CHANNEL_LOGO_URL.replace("=s160-", "=s800-")] if "=s160-" in CHANNEL_LOGO_URL else []
) + [CHANNEL_LOGO_URL]

_logo_cache: Image.Image | None = None
_logo_fetch_attempted = False


def _get_logo() -> Image.Image | None:
    global _logo_cache, _logo_fetch_attempted
    if _logo_cache is not None:
        return _logo_cache
    if _logo_fetch_attempted:
        return None
    _logo_fetch_attempted = True

    for url in _LOGO_URL_CANDIDATES:
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            _logo_cache = Image.open(io.BytesIO(response.content)).convert("RGB")
            return _logo_cache
        except Exception:
            continue
    logger.warning("No se pudo descargar el logo del canal, se usara una tarjeta de intro solo con texto")
    return None


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def _draw_text_intro_card(image: Image.Image, width: int, height: int) -> None:
    draw = ImageDraw.Draw(image)

    accent_thickness = max(4, height // 150)
    accent_y = height // 2
    draw.rectangle([0, accent_y, width, accent_y + accent_thickness], fill=_ACCENT_COLOR)

    title_font = _load_font("DejaVuSans-Bold.ttf", max(40, width // 10))
    title_text = CHANNEL_NAME.upper()
    title_box = draw.textbbox((0, 0), title_text, font=title_font)
    title_w, title_h = title_box[2] - title_box[0], title_box[3] - title_box[1]
    draw.text(
        ((width - title_w) / 2, accent_y - accent_thickness - title_h - 20),
        title_text,
        font=title_font,
        fill=TEXT_COLOR,
    )

    tagline_font = _load_font("DejaVuSans-Bold.ttf", max(20, width // 28))
    tagline_text = "TU INFORMADOR DE CONFIANZA"
    tagline_box = draw.textbbox((0, 0), tagline_text, font=tagline_font)
    tagline_w = tagline_box[2] - tagline_box[0]
    draw.text(
        ((width - tagline_w) / 2, accent_y + accent_thickness + 20),
        tagline_text,
        font=tagline_font,
        fill=_ACCENT_COLOR,
    )


def generate_intro_card(out_path: Path, width: int, height: int) -> Path:
    """Builds the opening scene every video starts with: the channel's real
    logo centered on its brand background. Falls back to a plain text-drawn
    card (name + tagline) if the logo can't be downloaded for any reason, so
    a network hiccup never breaks video generation."""
    image = Image.new("RGB", (width, height), _BACKGROUND_COLOR)

    logo = _get_logo()
    if logo is not None:
        logo_size = int(min(width, height) * 0.6)
        logo_resized = logo.resize((logo_size, logo_size))
        image.paste(logo_resized, ((width - logo_size) // 2, (height - logo_size) // 2))
    else:
        _draw_text_intro_card(image, width, height)

    image.save(out_path, quality=92)
    return out_path


def add_name_tag(image_path: Path, name: str, role: str) -> Path:
    """Draws a TV-news-style lower third (name + role over a solid bar near
    the bottom) directly onto a real public figure's photo, in place. Makes
    clear who's on screen instead of a plain unlabeled photo."""
    image = Image.open(image_path).convert("RGB")
    width, height = image.size

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_height = max(70, height // 9)
    bar_top = height - bar_height
    accent_thickness = max(4, bar_height // 12)
    draw.rectangle([0, bar_top, width, bar_top + accent_thickness], fill=_ACCENT_COLOR + (255,))
    draw.rectangle([0, bar_top + accent_thickness, width, height], fill=(0, 0, 0, 190))

    name_font = _load_font("DejaVuSans-Bold.ttf", max(22, bar_height // 3))
    name_y = bar_top + accent_thickness + bar_height // 10
    draw.text((width * 0.04, name_y), name.upper(), font=name_font, fill=TEXT_COLOR + (255,))

    if role:
        role_font = _load_font("DejaVuSans-Bold.ttf", max(16, bar_height // 4))
        name_box = draw.textbbox((0, 0), name.upper(), font=name_font)
        role_y = name_y + (name_box[3] - name_box[1]) + bar_height // 12
        draw.text((width * 0.04, role_y), role, font=role_font, fill=(220, 220, 220, 255))

    combined = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    combined.save(image_path, quality=92)
    return image_path
