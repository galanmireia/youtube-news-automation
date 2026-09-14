import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import VIDEO_HEIGHT, VIDEO_WIDTH


def _extract_frame(video_path: Path, out_path: Path, timestamp: float = 1.0) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video_path), "-frames:v", "1", str(out_path)],
        check=True,
        capture_output=True,
    )
    return out_path


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def generate_thumbnail(video_path: Path, title: str, out_path: Path) -> Path:
    frame_path = out_path.with_suffix(".frame.jpg")
    _extract_frame(video_path, frame_path)

    image = Image.open(frame_path).convert("RGB").resize((VIDEO_WIDTH, VIDEO_HEIGHT))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, VIDEO_HEIGHT - 320, VIDEO_WIDTH, VIDEO_HEIGHT], fill=(0, 0, 0, 160))

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
    except OSError:
        font = ImageFont.load_default()

    lines = _wrap_text(title.upper(), max_chars=22)
    y = VIDEO_HEIGHT - 290
    for line in lines:
        draw.text((60, y), line, font=font, fill=(255, 255, 255, 255))
        y += 90

    combined = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    combined.save(out_path, quality=92)
    frame_path.unlink(missing_ok=True)
    return out_path
