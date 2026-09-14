import logging
import random
import shutil
import time
from pathlib import Path
from typing import Callable

from . import storage
from .branding import INTRO_NARRATION
from .config import (
    BURN_SUBTITLES,
    DATA_DIR,
    LONG_VIDEO_HEIGHT,
    LONG_VIDEO_WIDTH,
    MUSIC_DIR,
    MUSIC_VOLUME,
    SHORT_VIDEO_HEIGHT,
    SHORT_VIDEO_WIDTH,
)
from .entity_extraction import extract_entities
from .news_source import fetch_candidate_news
from .script_generator import generate_script
from .subtitles import generate_subtitles
from .thumbnail import generate_thumbnail
from .tts import synthesize_scenes
from .video_builder import build_video, burn_subtitles, mix_background_music
from .visuals import fetch_clips_for_scenes

logger = logging.getLogger(__name__)

_VARIANT_DIMENSIONS = {
    "short": (SHORT_VIDEO_WIDTH, SHORT_VIDEO_HEIGHT),
    "long": (LONG_VIDEO_WIDTH, LONG_VIDEO_HEIGHT),
}
_VARIANT_ASPECT_RATIO = {"short": "9:16", "long": "16:9"}


_MUSIC_SUFFIXES = {".mp3", ".m4a", ".wav", ".aac", ".ogg"}


def _pick_music_track() -> Path | None:
    """One random track from the music folder, or None if there is no folder
    or nothing usable in it - music is optional, and a missing folder must
    never stop a video from being generated."""
    if not MUSIC_DIR.is_dir():
        return None
    tracks = sorted(p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in _MUSIC_SUFFIXES)
    if not tracks:
        logger.info("No hay pistas de musica en %s, el video se genera sin musica de fondo.", MUSIC_DIR)
        return None
    return random.choice(tracks)


def _generate_variant(news_item: dict, variant: str, work_dir: Path) -> int:
    width, height = _VARIANT_DIMENSIONS[variant]
    variant_dir = work_dir / variant
    variant_dir.mkdir(parents=True, exist_ok=True)

    script = generate_script(news_item, variant=variant)
    # Long videos open with a fixed bumper line over a branded title card, so
    # the channel has a consistent opening. Shorts don't: the first seconds
    # of a Short decide whether the viewer keeps watching or swipes, and a
    # logo card spends them on something that tells the viewer nothing. They
    # start on the hook instead.
    has_intro = variant == "long"
    if has_intro:
        intro_scene = {
            "narration": INTRO_NARRATION,
            "visual_keywords": "",
            "photo_subject": "",
            "photo_subject_role": "",
            "ai_image_prompt": "",
            "on_screen_highlight": "",
            "is_intro": True,
        }
        script["scenes"] = [intro_scene] + script["scenes"]
    # Default to treating the story as sensitive if the field is somehow
    # missing/unparseable - that only disables the extra narration-based
    # real-photo lookup below, never anything the model explicitly asked for.
    raw_sensitive = script.get("is_sensitive", True)
    is_sensitive = raw_sensitive.strip().lower() != "false" if isinstance(raw_sensitive, str) else bool(raw_sensitive)

    # A dedicated, isolated pass asking specifically "what named entities
    # appear in this text" is far more reliable than the model tagging
    # photo_subject correctly as one more field inside the much larger
    # script-generation prompt. Skipped for sensitive stories: it has no
    # way to guarantee it excludes a crime victim's name the way the
    # script prompt's own photo_subject rule does.
    if not is_sensitive:
        entities_by_scene = extract_entities(script["scenes"])
        for i, scene in enumerate(script["scenes"]):
            scene["detected_entities"] = entities_by_scene.get(i, [])

    narration_path, scene_durations = synthesize_scenes(script["scenes"], variant_dir / "audio")
    clip_entries = fetch_clips_for_scenes(
        script["scenes"],
        variant_dir / "clips",
        _VARIANT_ASPECT_RATIO[variant],
        scene_durations,
        is_sensitive=is_sensitive,
    )

    final_video_path = build_video(
        clip_entries,
        scene_durations,
        narration_path,
        variant_dir,
        variant_dir / "final_video.mp4",
        width,
        height,
        source_name=news_item.get("source_name", ""),
        intro_duration=scene_durations[0] if has_intro and scene_durations else 0.0,
    )

    # Two subtitle tracks off one transcription: a sentence-level SRT still
    # uploaded to YouTube as a toggleable caption track, plus a short-chunk
    # version burned into the picture (most of the Shorts feed is watched
    # muted, so on-screen text is what carries the narration).
    srt_path, burn_ass_path = generate_subtitles(
        narration_path, variant_dir / "subtitles.srt", variant_dir / "subtitles_burn.ass", width, height
    )

    # The thumbnail is grabbed from the video, so take it before burning in
    # subtitles - otherwise a random half-sentence ends up across the
    # thumbnail.
    thumbnail_path = generate_thumbnail(final_video_path, script["title"], variant_dir / "thumbnail.jpg", width, height)

    if BURN_SUBTITLES:
        final_video_path = burn_subtitles(final_video_path, burn_ass_path, variant_dir / "final_subtitled.mp4")

    music_path = _pick_music_track()
    if music_path is not None:
        final_video_path = mix_background_music(
            final_video_path, music_path, variant_dir / "final_with_music.mp4", MUSIC_VOLUME
        )

    video_id = storage.create_video_record(
        source_url=news_item["link"],
        variant=variant,
        title=script["title"],
        description=script["description"],
        tags=script["tags"],
        video_path=str(final_video_path),
        thumbnail_path=str(thumbnail_path),
        subtitle_path=str(srt_path),
    )
    logger.info("Video #%s (%s) generado y pendiente de aprobacion.", video_id, variant)
    return video_id


def cleanup_finished_video_files() -> int:
    """Deletes the on-disk working files (downloaded clips, audio, ffmpeg
    intermediates, final video/thumbnail/subtitles) for videos that are
    already uploaded or rejected - nothing ever needs them again once a
    video reaches one of those states, and leaving every run's files on
    disk forever eventually fills up the volume. Returns how many variant
    directories were removed."""
    removed = 0
    for video in storage.list_finished_videos():
        video_path = video["video_path"]
        if not video_path:
            continue
        variant_dir = Path(video_path).parent
        if variant_dir.exists():
            shutil.rmtree(variant_dir, ignore_errors=True)
            removed += 1
        job_dir = variant_dir.parent
        if job_dir.exists() and not any(job_dir.iterdir()):
            job_dir.rmdir()
    return removed


def run_once(
    on_variant_done: Callable[[int], None] | None = None,
    variants: tuple[str, ...] = ("short", "long"),
) -> list[int]:
    """Picks the next unprocessed news item and generates the requested
    variants for it (both a vertical Short and a longer horizontal video by
    default), storing each as 'pending'. Calls on_variant_done(video_id)
    right after each variant finishes, so callers can notify/send it
    immediately instead of waiting for all of them to be done. Returns the
    new videos' ids (empty if there was no fresh news)."""
    cleanup_finished_video_files()

    candidates = fetch_candidate_news(limit=5)
    if not candidates:
        logger.info("No hay noticias nuevas que procesar.")
        return []

    news_item = candidates[0]
    logger.info("Procesando noticia: %s", news_item["title"])

    work_dir = Path(DATA_DIR) / f"job_{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    video_ids = []
    for variant in variants:
        try:
            video_id = _generate_variant(news_item, variant, work_dir)
            video_ids.append(video_id)
            if on_variant_done is not None:
                on_variant_done(video_id)
        except Exception:
            # Don't let one variant's failure wipe out the other's already-finished
            # video: only the failed variant's own directory is cleaned up.
            logger.exception("Error generando la variante '%s'", variant)
            shutil.rmtree(work_dir / variant, ignore_errors=True)

    if video_ids:
        storage.mark_source_processed(news_item["link"])
    else:
        shutil.rmtree(work_dir, ignore_errors=True)

    return video_ids
