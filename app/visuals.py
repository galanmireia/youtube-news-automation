from pathlib import Path

import requests

from . import ai_images, real_photos
from .config import PEXELS_API_KEY

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

_PEXELS_ORIENTATION = {"9:16": "portrait", "16:9": "landscape"}
_TARGET_DIMENSIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}


def fetch_clip_for_scene(keywords: str, out_path: Path, aspect_ratio: str) -> Path:
    headers = {"Authorization": PEXELS_API_KEY}
    orientation = _PEXELS_ORIENTATION.get(aspect_ratio, "landscape")
    params = {"query": keywords, "per_page": 5, "orientation": orientation}
    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    videos = response.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No se encontraron videos de stock para: {keywords!r}")

    # Pick the video whose own orientation actually matches the target (Pexels'
    # "orientation" filter narrows the search but can still return the odd
    # mismatch), then the file closest to the target resolution. Fetching a
    # clip already shot in the right orientation avoids ffmpeg having to crop
    # a landscape clip down to a thin vertical sliver (or vice versa) later.
    target_width, target_height = _TARGET_DIMENSIONS.get(aspect_ratio, (1920, 1080))
    target_is_portrait = target_height > target_width

    def _video_matches_orientation(video: dict) -> bool:
        video_is_portrait = (video.get("height") or 0) > (video.get("width") or 0)
        return video_is_portrait == target_is_portrait

    matching_videos = [v for v in videos if _video_matches_orientation(v)] or videos
    video_files = sorted(
        matching_videos[0]["video_files"],
        key=lambda f: abs((f.get("width") or 0) - target_width) + abs((f.get("height") or 0) - target_height),
    )
    file_url = video_files[0]["link"]

    video_response = requests.get(file_url, timeout=60)
    video_response.raise_for_status()
    out_path.write_bytes(video_response.content)
    return out_path


def fetch_clips_for_scenes(scenes: list[dict], out_dir: Path, aspect_ratio: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_paths = []
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
        fetch_clip_for_scene(query, out_path, aspect_ratio)
        clip_paths.append(out_path)
    return clip_paths
