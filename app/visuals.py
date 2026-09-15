import logging
import math
import random
import time
from pathlib import Path

import requests

from . import ai_images, branding, real_photos
from .config import CHANNEL_NAME, PEXELS_API_KEY, PIXABAY_API_KEY

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"

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
# No single stock clip should hold the screen for much longer than this. A
# scene with a long narration used to get one clip for its whole length -
# one Short ended on a single shot held for 13 seconds, a quarter of the
# video.
#
# These were first set for a 60s Short, where a handful of scenes meant a
# handful of cuts. On a five-minute video the same rule produced 57 stock
# shots, one every five seconds, and that reads as randomness rather than
# pace: none of them illustrates anything in particular, so more of them only
# means more images that do not belong. Cutting the count roughly in third
# still keeps any one shot from outstaying nine seconds.
_MAX_SECONDS_PER_CLIP = 9.0
_MAX_CLIPS_PER_SCENE = 2

# requests' `timeout` only limits the wait between two chunks of data, so a
# download that trickles in forever never trips it. These cap the whole
# transfer as well, because a single stuck download is enough to freeze the
# generation thread - and that thread holds the lock that stops two
# generations overlapping, so the bot answers "ya hay una generacion en
# curso" to every /generar from then on.
_DOWNLOAD_TIMEOUT = (10, 30)
_DOWNLOAD_MAX_SECONDS = 120.0
# Deliberately small: the deadline below can only be checked between chunks,
# so a large chunk size would let a slow enough trickle sit inside a single
# read for minutes without the limit ever being looked at.
_DOWNLOAD_CHUNK = 64 << 10


def _search_pexels(query: str, orientation: str) -> list[dict]:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 8, "orientation": orientation}
    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    # Namespaced so an id can never collide with one from another library and
    # wrongly mark a different clip as already used.
    return [dict(v, id=f"pexels-{v['id']}") for v in response.json().get("videos", [])]


def _search_pixabay(query: str, orientation: str) -> list[dict]:
    """Second stock library, reshaped into the same fields as a Pexels result
    so the caller does not care where a clip came from.

    Returns nothing at all when no key is configured, and never raises: this
    is an extra chance at a good clip, so a library being down or rate-limited
    must cost nothing more than that chance."""
    if not PIXABAY_API_KEY:
        return []
    params = {"q": query, "video_type": "all", "per_page": 20, "key": PIXABAY_API_KEY}
    try:
        response = requests.get(PIXABAY_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        hits = response.json().get("hits", [])
    except Exception:
        logger.warning("Busqueda en Pixabay fallida para %r, se sigue solo con Pexels", query, exc_info=True)
        return []

    results = []
    for hit in hits:
        files = [
            {"link": f.get("url"), "width": f.get("width") or 0, "height": f.get("height") or 0}
            for f in (hit.get("videos") or {}).values()
            if f.get("url")
        ]
        if not files:
            continue
        best = max(files, key=lambda f: f["width"] * f["height"])
        results.append(
            {
                "id": f"pixabay-{hit.get('id')}",
                "width": best["width"],
                "height": best["height"],
                "video_files": files,
            }
        )
    return results


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

    def _choose(pool: list[dict]) -> dict:
        # Prefer a clip not already used elsewhere in this same video, and
        # pick randomly among the top matches (instead of always the single
        # top result) so the same query doesn't return the identical clip
        # every single time it's searched, in this video or in others.
        fresh = [v for v in pool if v["id"] not in used_video_ids]
        return random.choice((fresh or pool)[:5])

    # A landscape clip in a vertical Short survives only by being cropped to
    # the middle quarter of its frame, which throws away whatever the shot was
    # actually of. A wrong-shaped clip is therefore worth less than a
    # right-shaped clip from a vaguer search, so a query with no correctly
    # oriented result moves on to the broader query instead of settling. They
    # are kept aside all the same: a badly cropped clip still beats no video.
    chosen_video = None
    wrong_shape: list[dict] = []
    for query in queries:
        # Pixabay is only consulted when Pexels has nothing of the right shape
        # for this exact query - a correctly shaped clip from a second library
        # beats a broader, vaguer search of the first one.
        videos = _search_pexels(query, orientation)
        matching = [v for v in videos if _matches_orientation(v)]
        if not matching:
            wrong_shape.extend(videos)
            extra = _search_pixabay(query, orientation)
            matching = [v for v in extra if _matches_orientation(v)]
            wrong_shape.extend(v for v in extra if v not in matching)
            if matching:
                logger.info("Pexels no tenia nada vertical/horizontal para %r; usando Pixabay", query)
        if not matching:
            continue
        chosen_video = _choose(matching)
        break

    if chosen_video is None and wrong_shape:
        logger.info(
            "Sin clips con la orientacion correcta para %r; se usa uno recortado.", keywords
        )
        chosen_video = _choose(wrong_shape)

    if chosen_video is None:
        raise RuntimeError(f"No se encontraron videos de stock ni con la busqueda de respaldo para: {keywords!r}")

    used_video_ids.add(chosen_video["id"])
    video_file = _pick_video_file(chosen_video, target_width, target_height)

    _download_to_file(video_file["link"], out_path)
    return out_path


def _download_to_file(url: str, out_path: Path) -> None:
    """Streams a clip straight to disk under a total time limit.

    Reading into memory first (`response.content`) meant a 4K clip sat in RAM
    in full before being written, on top of the whisper model already loaded
    in the same process; streaming keeps only one chunk at a time."""
    deadline = time.monotonic() + _DOWNLOAD_MAX_SECONDS
    with requests.get(url, timeout=_DOWNLOAD_TIMEOUT, stream=True) as response:
        response.raise_for_status()
        with out_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK):
                if time.monotonic() > deadline:
                    raise TimeoutError(f"La descarga de {url} supero los {_DOWNLOAD_MAX_SECONDS:.0f}s")
                fh.write(chunk)


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
        # The closing scene asks viewers to subscribe, so the channel's own
        # name gets picked up as an entity. Looking it up is pointless, and a
        # loose match would put some unrelated image on screen captioned with
        # the channel name.
        candidates = [name for name in candidates if name.strip().lower() != CHANNEL_NAME.strip().lower()]

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

        # visual_keywords can be intentionally empty when the scene expected a
        # photo/AI image to be used instead; if that failed, fall back to
        # something Pexels can still search for instead of an empty query.
        # photo_subject is deliberately not part of this chain: it is a Spanish
        # proper noun meant for Wikipedia, and Pexels indexes in English, so
        # searching it returns nothing useful - a scene about Pekin searched
        # Pexels for "Pekin" and fell through to generic footage anyway.
        query = (scene.get("visual_keywords") or "").strip() or ai_image_prompt or _LAST_RESORT_QUERY
        # A long scene gets several clips rather than one held for its whole
        # length. Each search excludes the clips already used, so they differ.
        clip_count = min(_MAX_CLIPS_PER_SCENE, max(1, math.ceil(duration / _MAX_SECONDS_PER_CLIP)))
        # Only the first clip carries the caption: repeating it on every cut
        # of the same scene would make it flash in and out repeatedly.
        highlight = (scene.get("on_screen_highlight") or "").strip()
        scene_entries: list[tuple[Path, dict | None]] = []
        for j in range(clip_count):
            out_path = out_dir / f"clip_{i:02d}_{j}.mp4"
            logger.info("Escena %s: buscando clip %s/%s en Pexels para %r...", i, j + 1, clip_count, query)
            fetch_clip_for_scene(query, out_path, aspect_ratio, used_video_ids)
            tag = {"caption": highlight} if highlight and j == 0 else None
            scene_entries.append((out_path, tag))
        clip_entries.append(scene_entries)
    return clip_entries
