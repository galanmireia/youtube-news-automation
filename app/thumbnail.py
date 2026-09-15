import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat

# Fractions of the video to consider for the thumbnail still. All well past
# the intro card: sampling near the start meant every thumbnail was just the
# channel logo instead of anything from the story itself.
_CANDIDATE_POSITIONS = (0.25, 0.40, 0.55, 0.70)


def _extract_frame(video_path: Path, out_path: Path, timestamp: float) -> Path | None:
    result = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video_path), "-frames:v", "1", str(out_path)],
        capture_output=True,
    )
    return out_path if result.returncode == 0 and out_path.exists() else None


def _video_duration(video_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
    )
    try:
        return float(result.stdout.decode().strip())
    except ValueError:
        return 0.0


def _pick_frame(video_path: Path, work_path: Path) -> Path:
    """Picks the most visually interesting of several candidate stills rather
    than always grabbing the same timestamp: a shot that happens to be a
    near-black or near-empty frame makes a dead thumbnail. Standard deviation
    across the image is a decent stand-in for "has some contrast and detail"."""
    duration = _video_duration(video_path)
    best_path, best_score = None, -1.0
    for index, position in enumerate(_CANDIDATE_POSITIONS):
        candidate = work_path.with_suffix(f".cand{index}.jpg")
        timestamp = duration * position if duration else 1.0
        if _extract_frame(video_path, candidate, timestamp) is None:
            continue
        with Image.open(candidate) as image:
            score = sum(ImageStat.Stat(image.convert("RGB")).stddev) / 3
        if score > best_score:
            if best_path is not None:
                best_path.unlink(missing_ok=True)
            best_path, best_score = candidate, score
        else:
            candidate.unlink(missing_ok=True)

    if best_path is None:
        fallback = work_path.with_suffix(".cand.jpg")
        if _extract_frame(video_path, fallback, 1.0) is None:
            raise RuntimeError(f"No se pudo extraer ningun fotograma de {video_path}")
        return fallback
    return best_path


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fit_title(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, max_lines: int):
    """Shrinks the title until it actually fits the frame. The previous code
    estimated how many characters fit from the font size, which is only a
    guess - real titles ran off the right edge, cut mid-word."""
    size = start_size
    while size > 20:
        font = _load_font(size)
        lines = _wrap_to_width(draw, text, font, max_width)
        if len(lines) <= max_lines and all(draw.textbbox((0, 0), l, font=font)[2] <= max_width for l in lines):
            return font, lines
        size -= 2
    font = _load_font(20)
    return font, _wrap_to_width(draw, text, font, max_width)[:max_lines]


def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
    """Fills the frame without distorting it.

    The previous version resized straight to the target, which for a vertical
    Short turned into a horizontal thumbnail meant squashing 9:16 into 16:9 -
    the ship got fat and the illustration bent. Scaling to cover and cropping
    the overflow keeps everything the shape it was drawn."""
    origen_w, origen_h = image.size
    escala = max(width / origen_w, height / origen_h)
    nuevo = image.resize((max(1, round(origen_w * escala)), max(1, round(origen_h * escala))))
    izquierda = (nuevo.width - width) // 2
    # Cropped from the upper third rather than the centre: the lower part of a
    # frame is where this pipeline puts its own name bars and caption boxes.
    arriba = min(max(0, (nuevo.height - height) // 3), max(0, nuevo.height - height))
    return nuevo.crop((izquierda, arriba, izquierda + width, arriba + height))


def _thumbnail_text(title: str) -> str:
    """The part of the title worth putting on the picture.

    A full headline set large enough to read at listing size needs three lines
    and buries the image. Titles here are built as "Subject: the hook", so the
    hook alone is both the shorter half and the interesting one; failing that,
    the first few words."""
    texto = title.strip()
    for separador in (": ", " - ", " | ", "? ", "; "):
        if separador in texto:
            cabeza, _, cola = texto.partition(separador)
            # Keep whichever half actually says something, preferring the hook.
            texto = cola if len(cola.split()) >= 3 else cabeza
            break
    palabras = texto.split()
    if len(palabras) > 7:
        texto = " ".join(palabras[:7])
    return texto.upper().rstrip(" ,.;:")


def generate_thumbnail(video_path: Path, title: str, out_path: Path, width: int, height: int) -> Path:
    frame_path = _pick_frame(video_path, out_path)
    image = _cover(Image.open(frame_path).convert("RGB"), width, height)

    margin = int(width * 0.04)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Two lines, not three. A three-line band swallowed more than half the
    # picture, which defeats the point of choosing an interesting frame in the
    # first place - the thumbnail has to be read at the size of a phone
    # listing, where a picture and four words beat a whole sentence.
    font, lines = _fit_title(
        draw, _thumbnail_text(title), max_width=width - margin * 2,
        start_size=max(36, width // 11), max_lines=2,
    )

    line_height = int(font.size * 1.22)
    band_height = line_height * len(lines) + margin * 2
    band_top = height - band_height
    draw.rectangle([0, band_top, width, height], fill=(0, 0, 0, 175))
    draw.rectangle([0, band_top, width, band_top + max(4, height // 300)], fill=(196, 30, 42, 255))

    y = band_top + margin
    for line in lines:
        draw.text((margin, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    combined = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    combined.save(out_path, quality=92)
    frame_path.unlink(missing_ok=True)
    return out_path
