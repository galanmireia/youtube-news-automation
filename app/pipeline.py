import logging
import shutil
import time
from pathlib import Path

from . import storage
from .config import DATA_DIR, LONG_VIDEO_HEIGHT, LONG_VIDEO_WIDTH, SHORT_VIDEO_HEIGHT, SHORT_VIDEO_WIDTH
from .news_source import fetch_candidate_news
from .script_generator import generate_script
from .subtitles import generate_srt
from .thumbnail import generate_thumbnail
from .tts import synthesize_scenes
from .video_builder import build_video, burn_subtitles
from .visuals import fetch_clips_for_scenes

logger = logging.getLogger(__name__)

_VARIANT_DIMENSIONS = {
    "short": (SHORT_VIDEO_WIDTH, SHORT_VIDEO_HEIGHT),
    "long": (LONG_VIDEO_WIDTH, LONG_VIDEO_HEIGHT),
}


def _generate_variant(news_item: dict, variant: str, work_dir: Path) -> int:
    width, height = _VARIANT_DIMENSIONS[variant]
    variant_dir = work_dir / variant
    variant_dir.mkdir(parents=True, exist_ok=True)

    script = generate_script(news_item, variant=variant)
    narration_path, scene_durations = synthesize_scenes(script["scenes"], variant_dir / "audio")
    clip_paths = fetch_clips_for_scenes(script["scenes"], variant_dir / "clips")

    raw_video_path = build_video(
        clip_paths, scene_durations, narration_path, variant_dir, variant_dir / "raw_video.mp4", width, height
    )

    srt_path = generate_srt(narration_path, variant_dir / "subtitles.srt")
    final_video_path = burn_subtitles(raw_video_path, srt_path, variant_dir / "final_video.mp4")

    thumbnail_path = generate_thumbnail(final_video_path, script["title"], variant_dir / "thumbnail.jpg", width, height)

    video_id = storage.create_video_record(
        source_url=news_item["link"],
        variant=variant,
        title=script["title"],
        description=script["description"],
        tags=script["tags"],
        video_path=str(final_video_path),
        thumbnail_path=str(thumbnail_path),
    )
    logger.info("Video #%s (%s) generado y pendiente de aprobacion.", video_id, variant)
    return video_id


def run_once() -> list[int]:
    """Picks the next unprocessed news item and generates both a vertical
    Short and a longer horizontal video for it, storing each as 'pending'.
    Returns the new videos' ids (empty if there was no fresh news)."""
    candidates = fetch_candidate_news(limit=5)
    if not candidates:
        logger.info("No hay noticias nuevas que procesar.")
        return []

    news_item = candidates[0]
    logger.info("Procesando noticia: %s", news_item["title"])

    work_dir = Path(DATA_DIR) / f"job_{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        video_ids = [_generate_variant(news_item, variant, work_dir) for variant in ("short", "long")]
        storage.mark_source_processed(news_item["link"])
        return video_ids
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
