import logging
import random
from pathlib import Path

import requests

from . import ai_images, branding, real_photos
from .config import PEXELS_API_KEY

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

_PEXELS_ORIENTATION = {"9:16": "portrait", "16:9": "landscape"}
_TARGET_DIMENSIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
# Always has plenty of Pexels matches, used only if every other query (the
# scene's own keywords, then a broadened version of them) comes up empty.
_LAST_RESORT_QUERY = "news broadcast studio"
# Showing more than 2 real photos in one shot would make already-short
# scenes feel like a rapid-fire slideshow instead of an actual news video.
_MAX_PHOTOS_PER_SCENE = 2
# Splitting a scene's screen time only makes sense if each resulting photo
# still gets a readable amount of time on screen.
_MIN_SCENE_SECONDS_FOR_MULTI_PHOTO = 6.0


def _search_pexels(query: str, orientation: str) -> list[dict]:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 8, "orientation": orientation}
    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("videos", [])


def _pick_video_file(video: dict, target_width: int, target_height: int) -> dict:
    return min(
        video["video_files"],
        key=lambda f: abs((f.get("width") or 0) - target_width) + abs((f.get("height") or 0) - target_height),
    )


def fetch_clip_for_scene(keywords: str, out_path: Path, aspect_ratio: str, used_video_ids: set[int]) -> Path:
    orientation = _PEXELS_ORIENTATION.get(aspect_ratio, "landscape")
    target_width, target_height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
    target_is_portrait = target_height > target_width

    def _matches_orientation(video: dict) -> bool:
        return ((video.get("height") or 0) > (video.get("width") or 0)) == target_is_portrait

    # Try the scene's own (now fairly specific) keywords first; a query that
    # happens to have zero Pexels matches falls back to a broader version of
    # itself, then to a universal query, instead of crashing the whole video.
    # Broaden by dropping words from the END, never by keeping only the last
    # one: the country leads these phrases ("mexico city street protest"), so
    # falling back to the tail ("protest") threw away precisely the word
    # keeping the footage in the right country - which is how a Hungarian
    # flag ended up in a scene about Mexico.
    words = keywords.split()
    queries = [keywords]
    for cut in range(len(words) - 1, 0, -1):
        broader = " ".join(words[:cut])
        if broader not in queries:
            queries.append(broader)
    queries.append(_LAST_RESORT_QUERY)

    chosen_video = None
    for query in queries:
        videos = _search_pexels(query, orientation)
        if not videos:
            continue
        candidates = [v for v in videos if _matches_orientation(v)] or videos
        # Prefer a clip not already used elsewhere in this same video, and
        # pick randomly among the top matches (instead of always the single
        # top result) so the same query doesn't return the identical clip
        # every single time it's searched, in this video or in others.
        fresh = [v for v in candidates if v["id"] not in used_video_ids]
        pool = fresh or candidates
        chosen_video = random.choice(pool[:5])
        break

    if chosen_video is None:
        raise RuntimeError(f"No se encontraron videos de stock ni con la busqueda de respaldo para: {keywords!r}")

    used_video_ids.add(chosen_video["id"])
    video_file = _pick_video_file(chosen_video, target_width, target_height)

    video_response = requests.get(video_file["link"], timeout=60)
    video_response.raise_for_status()
    out_path.write_bytes(video_response.content)
    return out_path


def fetch_clips_for_scenes(
    scenes: list[dict], out_dir: Path, aspect_ratio: str, scene_durations: list[float], is_sensitive: bool = False
) -> list[list[tuple[Path, dict | None]]]:
    """Returns, per scene, a list of (clip_path, name_tag) entries - normally
    just one, but up to _MAX_PHOTOS_PER_SCENE when a scene names several
    entities and is long enough to show more than one of them, so a single
    sentence mentioning two parties/institutions doesn't only ever display
    the first one."""
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_entries: list[list[tuple[Path, dict | None]]] = []
    used_video_ids: set[int] = set()
    # Stock clips were already deduplicated, but real photos weren't: an
    # entity named in several scenes (e.g. "Junta Electoral Central") showed
    # the identical picture every time, which read as the video looping.
    used_photo_urls: set[str] = set()
    for i, scene in enumerate(scenes):
        duration = scene_durations[i] if i < len(scene_durations) else 0.0

        if scene.get("is_intro"):
            width, height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
            card_path = branding.generate_intro_card(out_dir / f"clip_{i:02d}.jpg", width, height)
            clip_entries.append([(card_path, None)])
            continue

        photo_subject = (scene.get("photo_subject") or "").strip()
        # detected_entities comes from a dedicated Claude pass over the
        # final narration (see entity_extraction.py) - far more reliable
        # than the model's own inline photo_subject tagging alone. It's
        # never populated for sensitive stories (pipeline.py skips that
        # call entirely there), since it has no guaranteed way to exclude
        # a crime victim's name the way photo_subject's own prompt rule
        # does - only the model's explicit photo_subject is trusted then.
        detected_entities = [] if is_sensitive else (scene.get("detected_entities") or [])
        extra_candidates = [e.get("name", "").strip() for e in detected_entities if e.get("name", "").strip()]
        candidates = ([photo_subject] if photo_subject else []) + [
            name for name in dict.fromkeys(extra_candidates) if name != photo_subject
        ]

        max_photos = _MAX_PHOTOS_PER_SCENE if duration >= _MIN_SCENE_SECONDS_FOR_MULTI_PHOTO else 1
        found: list[tuple[str, Path, str]] = []
        for candidate in candidates:
            if len(found) >= max_photos:
                break
            candidate_path = out_dir / f"clip_{i:02d}_{len(found)}.jpg"
            result = real_photos.fetch_portrait(candidate, candidate_path, exclude_urls=used_photo_urls)
            if result is not None:
                photo_path, photo_url = result
                used_photo_urls.add(photo_url)
                role = (
                    (scene.get("photo_subject_role") or "").strip()
                    if candidate == photo_subject
                    else next((e.get("descriptor", "") for e in detected_entities if e.get("name") == candidate), "")
                )
                found.append((candidate, photo_path, role))

        if candidates:
            logger.info(
                "Escena %s: candidatos a foto real %s -> %s",
                i,
                candidates,
                f"encontradas: {[name for name, _, _ in found]}" if found else "ninguna foto encontrada",
            )

        if found:
            clip_entries.append([(path, {"name": name, "role": role}) for name, path, role in found])
            continue

        ai_image_prompt = (scene.get("ai_image_prompt") or "").strip()
        if ai_image_prompt:
            image_path = ai_images.generate_image(ai_image_prompt, out_dir / f"clip_{i:02d}.jpg", aspect_ratio)
            if image_path is not None:
                clip_entries.append([(image_path, None)])
                continue

        out_path = out_dir / f"clip_{i:02d}.mp4"
        # visual_keywords can be intentionally empty when the scene expected a
        # photo/AI image to be used instead; if that failed, fall back to
        # something Pexels can still search for instead of an empty query.
        query = (scene.get("visual_keywords") or "").strip() or ai_image_prompt or photo_subject or "news studio background"
        fetch_clip_for_scene(query, out_path, aspect_ratio, used_video_ids)
        # A scene that lands here has no real photo tied to what's being
        # said - overlay the scene's own key fact so the point doesn't get
        # lost in an otherwise generic stock shot.
        highlight = (scene.get("on_screen_highlight") or "").strip()
        clip_entries.append([(out_path, {"caption": highlight} if highlight else None)])
    return clip_entries
