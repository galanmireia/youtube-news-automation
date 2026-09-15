import logging
import random
import shutil
import threading
import time
from pathlib import Path
from typing import Callable

from . import llm_usage, storage
from .branding import INTRO_NARRATION
from .config import (
    BURN_SUBTITLES,
    CONTENT_MODE,
    DATA_DIR,
    LONG_VIDEO_HEIGHT,
    LONG_VIDEO_WIDTH,
    MUSIC_DIR,
    MUSIC_VOLUME,
    SHORT_VIDEO_HEIGHT,
    SHORT_VIDEO_WIDTH,
)
from .entity_extraction import extract_entities
from .news_picker import pick_best_story
from .news_source import fetch_candidate_news
from .topic_source import fetch_candidate_topics
from .script_generator import generate_script
from .subtitles import generate_subtitles
from .thumbnail import generate_thumbnail
from .tts import synthesize_scenes
from .video_builder import build_video, burn_subtitles, mix_background_music
from .visuals import fetch_clips_for_scenes

logger = logging.getLogger(__name__)

# Set by request_stop() (the bot's /parar) and cleared at the start of every
# run. A generation is a chain of single blocking calls - an API request, an
# ffmpeg run - with nowhere inside them to check a flag, so a stop can only
# take effect between stages, not instantly.
_stop_requested = threading.Event()


class GenerationStopped(Exception):
    """Raised at a stage boundary when a stop has been requested."""


def request_stop() -> None:
    """Asks the running generation to give up at its next stage boundary."""
    _stop_requested.set()


def stop_requested() -> bool:
    """Whether the run that just finished ended because a stop was asked for.
    The flag survives until the next run clears it, so a caller can tell a
    stopped run apart from one that simply had nothing to do."""
    return _stop_requested.is_set()


def _stage(variant: str, number: int, message: str, *args) -> None:
    """Announces a stage, and aborts the generation here if a stop was asked
    for. Every stage goes through this, so a stop is honoured at whichever
    boundary comes next rather than only between variants."""
    if _stop_requested.is_set():
        raise GenerationStopped(f"parada pedida antes de [{variant}] {number}/7")
    logger.info("[%s] %s/7 " + message, variant, number, *args)

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

    # Each stage announces itself before it starts, not after. When a step
    # froze with no error, the log simply stopped mid-run and there was no way
    # to tell from it which call was stuck - the stage had to be inferred from
    # whichever incidental line happened to be logged last.
    _stage(variant, 1, "Escribiendo el guion...")
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
        _stage(variant, 2, "Extrayendo entidades del guion...")
        entities_by_scene = extract_entities(script["scenes"])
        for i, scene in enumerate(script["scenes"]):
            scene["detected_entities"] = entities_by_scene.get(i, [])

    _stage(variant, 3, "Generando la narracion con TTS (%s escenas)...", len(script["scenes"]))
    narration_path, scene_durations = synthesize_scenes(script["scenes"], variant_dir / "audio")

    _stage(variant, 4, "Buscando imagenes y videos para las escenas...")
    clip_entries = fetch_clips_for_scenes(
        script["scenes"],
        variant_dir / "clips",
        _VARIANT_ASPECT_RATIO[variant],
        scene_durations,
        is_sensitive=is_sensitive,
    )

    _stage(variant, 5, "Montando el video con ffmpeg...")
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
    _stage(variant, 6, "Transcribiendo para los subtitulos...")
    srt_path, burn_ass_path = generate_subtitles(
        narration_path,
        variant_dir / "subtitles.srt",
        variant_dir / "subtitles_burn.ass",
        width,
        height,
        # The narration is this exact text spoken aloud, so the transcription
        # is only needed for its timings - the wording is already known, and
        # trusting the transcription for it burns misheard names into the
        # picture.
        script_text=" ".join(scene.get("narration", "") for scene in script["scenes"]),
    )

    # The thumbnail is grabbed from the video, so take it before burning in
    # subtitles - otherwise a random half-sentence ends up across the
    # thumbnail.
    _stage(variant, 7, "Miniatura, subtitulos incrustados y musica...")
    thumbnail_path = generate_thumbnail(final_video_path, script["title"], variant_dir / "thumbnail.jpg", width, height)

    if BURN_SUBTITLES:
        final_video_path = burn_subtitles(final_video_path, burn_ass_path, variant_dir / "final_subtitled.mp4")

    music_path = _pick_music_track()
    if music_path is not None:
        final_video_path = mix_background_music(
            final_video_path, music_path, variant_dir / "final_with_music.mp4", MUSIC_VOLUME
        )

    # Everything else in this directory was scaffolding for the build: the
    # downloaded stock clips and photos, the per-scene audio, the rendered
    # scene segments and every ffmpeg intermediate. Together they dwarf the
    # three files that are actually needed from here on, and they were being
    # kept until the video was uploaded or rejected - so a few videos waiting
    # for approval filled the volume and the next build died with "No space
    # left on device".
    _discard_build_files(variant_dir, keep={final_video_path, thumbnail_path, srt_path})

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



def _discard_build_files(variant_dir: Path, keep: set[Path]) -> int:
    """Removes everything under a finished variant's directory except the
    files that are still needed - the video itself, its thumbnail and its
    subtitle track. Returns the megabytes freed."""
    keep_resolved = {path.resolve() for path in keep}
    freed = 0
    for path in sorted(variant_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            # Only removes it if the loop above already emptied it.
            try:
                path.rmdir()
            except OSError:
                pass
            continue
        if path.resolve() in keep_resolved:
            continue
        freed += path.stat().st_size
        path.unlink(missing_ok=True)
    if freed:
        logger.info("Limpieza: %.0f MB de ficheros intermedios eliminados.", freed / 1e6)
    return freed


def sweep_orphan_build_files() -> int:
    """One pass over the whole data directory removing files no video record
    points at any more.

    Builds used to leave their scaffolding behind until the video was uploaded
    or rejected, and a failed run could leave a whole job directory with no
    record at all. That filled the volume - a build died with "No space left
    on device" with 4.8GB of a 5GB disk used. New builds clean up after
    themselves now; this clears what earlier ones left. Returns megabytes
    freed."""
    keep = {Path(path).resolve() for path in storage.all_referenced_paths()}
    freed = 0
    for job_dir in Path(DATA_DIR).glob("job_*"):
        for path in sorted(job_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
                continue
            if path.resolve() in keep:
                continue
            freed += path.stat().st_size
            path.unlink(missing_ok=True)
        if job_dir.is_dir() and not any(job_dir.iterdir()):
            job_dir.rmdir()
    if freed:
        logger.info("Limpieza de arranque: %.0f MB de ficheros huerfanos eliminados.", freed / 1e6)
    return freed


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
    _stop_requested.clear()
    cleanup_finished_video_files()

    if CONTENT_MODE == "topics":
        candidates = fetch_candidate_topics(limit=3)
    else:
        candidates = fetch_candidate_news(limit=6)
    if not candidates:
        logger.info("No hay temas nuevos que procesar.")
        return []

    # Which story gets made matters more than how well it is made: a
    # procedural court filing and a story with a person in it are not worth
    # the same 60 seconds, and taking whichever headline came first made that
    # choice at random.
    if CONTENT_MODE == "topics":
        # No picker here. The picker exists to judge which of six headlines the
        # feed happened to push is worth making, and to refuse the ones the
        # channel must not touch. The catalogue is already curated and ordered,
        # so that judgement was made when it was written - and asking the model
        # to re-make it over three nine-thousand-character articles would cost
        # more than the script itself.
        news_item = candidates[0]
    else:
        news_item = pick_best_story(candidates)
        if news_item is None:
            # The picker also enforces which stories the channel must not make,
            # so there is no safe default to fall back on here.
            logger.info("No se ha podido elegir noticia con garantias; no se genera nada.")
            return []
    logger.info("Procesando noticia: %s", news_item["title"])

    work_dir = Path(DATA_DIR) / f"job_{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    video_ids = []
    for variant in variants:
        try:
            video_id = _generate_variant(news_item, variant, work_dir)
            resumen_coste = llm_usage.report_and_reset()
            if resumen_coste:
                logger.info("[%s] %s", variant, resumen_coste)
            video_ids.append(video_id)
            if on_variant_done is not None:
                on_variant_done(video_id)
        except GenerationStopped as exc:
            logger.info("Generacion detenida a peticion: %s", exc)
            shutil.rmtree(work_dir / variant, ignore_errors=True)
            break
        except Exception:
            # Don't let one variant's failure wipe out the other's already-finished
            # video: only the failed variant's own directory is cleaned up.
            logger.exception("Error generando la variante '%s'", variant)
            shutil.rmtree(work_dir / variant, ignore_errors=True)

    if video_ids:
        storage.mark_source_processed(news_item["link"], news_item.get("title", ""))
    else:
        shutil.rmtree(work_dir, ignore_errors=True)

    return video_ids
