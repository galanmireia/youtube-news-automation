import random
from pathlib import Path

import requests

from . import ai_images, real_photos
from .config import PEXELS_API_KEY

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

_PEXELS_ORIENTATION = {"9:16": "portrait", "16:9": "landscape"}
_TARGET_DIMENSIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
# Always has plenty of Pexels matches, used only if every other query (the
# scene's own keywords, then a broadened version of them) comes up empty.
_LAST_RESORT_QUERY = "news broadcast studio"


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
    words = keywords.split()
    queries = [keywords]
    if len(words) > 1:
        queries.append(words[-1])
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


def fetch_clips_for_scenes(scenes: list[dict], out_dir: Path, aspect_ratio: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_paths = []
    used_video_ids: set[int] = set()
    for i, scene in enumerate(scenes):
        photo_subject = (scene.get("photo_subject") or "").strip()
        if photo_subject:
            photo_path = real_photos.fetch_portrait(photo_subject, out_dir / f"clip_{i:02d}.jpg")
            if photo_path is not None:
                clip_paths.append(photo_path)
                continue

        ai_image_prompt = (scene.get("ai_image_prompt") or "").strip()
        if ai_image_prompt:
            image_path = ai_images.generate_image(ai_image_prompt, out_dir / f"clip_{i:02d}.jpg", aspect_ratio)
            if image_path is not None:
                clip_paths.append(image_path)
                continue

        out_path = out_dir / f"clip_{i:02d}.mp4"
        # visual_keywords can be intentionally empty when the scene expected a
        # photo/AI image to be used instead; if that failed, fall back to
        # something Pexels can still search for instead of an empty query.
        query = (scene.get("visual_keywords") or "").strip() or ai_image_prompt or photo_subject or "news studio background"
        fetch_clip_for_scene(query, out_path, aspect_ratio, used_video_ids)
        clip_paths.append(out_path)
    return clip_paths
