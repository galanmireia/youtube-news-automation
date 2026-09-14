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


def image_aspect_ratio(path: Path) -> float:
    with Image.open(path) as image:
        return image.width / image.height


def name_tag_bar_height(frame_height: int) -> int:
    """Bar height as a fraction of the frame - noticeably smaller than the
    old baked-in version (which was ~1/9th of the frame and stayed on
    screen for the whole shot) since it now only needs to read clearly
    during its brief slide-in/hold/slide-out instead of being a permanent
    fixture."""
    return max(50, frame_height // 13)


def render_name_tag_bar(name: str, role: str, width: int, bar_height: int) -> Image.Image:
    """Renders just the TV-news-style lower third (name + role over a solid
    bar) as its own transparent image, sized to the bar's own height rather
    than the full frame. video_builder composites this onto the photo with
    an animated vertical position (sliding up from off-screen, holding
    briefly, sliding back down) instead of baking it permanently into the
    photo, so it reads as a temporary caption rather than a fixed label."""
    bar = Image.new("RGBA", (width, bar_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)

    accent_thickness = max(3, bar_height // 12)
    draw.rectangle([0, 0, width, accent_thickness], fill=_ACCENT_COLOR + (255,))
    draw.rectangle([0, accent_thickness, width, bar_height], fill=(0, 0, 0, 190))

    name_font = _load_font("DejaVuSans-Bold.ttf", max(18, bar_height // 3))
    name_y = accent_thickness + bar_height // 10
    draw.text((width * 0.04, name_y), name.upper(), font=name_font, fill=TEXT_COLOR + (255,))

    if role:
        role_font = _load_font("DejaVuSans-Bold.ttf", max(13, bar_height // 5))
        name_box = draw.textbbox((0, 0), name.upper(), font=name_font)
        role_y = name_y + (name_box[3] - name_box[1]) + bar_height // 14
        draw.text((width * 0.04, role_y), role, font=role_font, fill=(220, 220, 220, 255))

    return bar


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:max_lines]


def render_highlight_box(text: str, box_width: int, box_height: int) -> Image.Image:
    """Small caption card for scenes that end up using generic stock video
    (no real photo tied to what's being said) - shows the scene's own key
    fact so the point doesn't get lost in an otherwise generic shot."""
    box = Image.new("RGBA", (box_width, box_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(box)

    draw.rounded_rectangle([0, 0, box_width, box_height], radius=box_height // 6, fill=(0, 0, 0, 190))
    accent_width = max(4, box_width // 45)
    draw.rectangle([0, 0, accent_width, box_height], fill=_ACCENT_COLOR + (255,))

    text_left = accent_width + box_height // 4
    font = _load_font("DejaVuSans-Bold.ttf", max(16, box_height // 4))
    lines = _wrap_text(draw, text.upper(), font, box_width - text_left - box_height // 6, max_lines=2)

    line_height = font.size + 6
    total_h = line_height * len(lines)
    y = (box_height - total_h) / 2
    for line in lines:
        draw.text((text_left, y), line, font=font, fill=TEXT_COLOR + (255,))
        y += line_height

    return box


def render_source_caption(source_name: str, width: int, height: int) -> Image.Image:
    """Small, unobtrusive source-attribution tag shown in a corner for the
    whole video (after the intro) - crediting where the story comes from so
    the channel's facts read as sourced instead of just asserted."""
    font_size = max(14, height // 45)
    font = _load_font("DejaVuSans-Bold.ttf", font_size)
    text = f"FUENTE: {source_name.upper()}"

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_box = probe.textbbox((0, 0), text, font=font)
    pad = font_size // 2
    tag_w, tag_h = text_box[2] - text_box[0] + pad * 2, text_box[3] - text_box[1] + pad * 2

    tag = Image.new("RGBA", (tag_w, tag_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tag)
    draw.rounded_rectangle([0, 0, tag_w, tag_h], radius=tag_h // 4, fill=(0, 0, 0, 165))
    draw.text((pad - text_box[0], pad - text_box[1]), text, font=font, fill=(220, 220, 220, 255))
    return tag
