import logging
import shutil
import time

from . import storage
from .config import DATA_DIR
from .news_source import fetch_candidate_news
from .script_generator import generate_script
from .subtitles import generate_srt
from .thumbnail import generate_thumbnail
from .tts import synthesize_scenes
from .video_builder import build_video, burn_subtitles
from .visuals import fetch_clips_for_scenes

logger = logging.getLogger(__name__)


def run_once() -> int | None:
    """Picks the next unprocessed news item, generates a full video for it
    and stores it as 'pending'. Returns the new video's id, or None if there
    was no fresh news to process."""
    candidates = fetch_candidate_news(limit=5)
    if not candidates:
        logger.info("No hay noticias nuevas que procesar.")
        return None

    news_item = candidates[0]
    logger.info("Procesando noticia: %s", news_item["title"])

    work_dir = DATA_DIR / f"job_{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        script = generate_script(news_item)
        narration_path, scene_durations = synthesize_scenes(script["scenes"], work_dir / "audio")
        clip_paths = fetch_clips_for_scenes(script["scenes"], work_dir / "clips")

        raw_video_path = build_video(
            clip_paths, scene_durations, narration_path, work_dir, work_dir / "raw_video.mp4"
        )

        srt_path = generate_srt(narration_path, work_dir / "subtitles.srt")
        final_video_path = burn_subtitles(raw_video_path, srt_path, work_dir / "final_video.mp4")

        thumbnail_path = generate_thumbnail(final_video_path, script["title"], work_dir / "thumbnail.jpg")

        video_id = storage.create_video_record(
            source_url=news_item["link"],
            title=script["title"],
            description=script["description"],
            tags=script["tags"],
            video_path=str(final_video_path),
            thumbnail_path=str(thumbnail_path),
        )
        storage.mark_source_processed(news_item["link"])
        logger.info("Video #%s generado y pendiente de aprobacion.", video_id)
        return video_id
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
