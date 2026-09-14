from pathlib import Path

import requests

from . import real_photos
from .config import PEXELS_API_KEY

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


def fetch_clip_for_scene(keywords: str, out_path: Path) -> Path:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keywords, "per_page": 5, "orientation": "landscape"}
    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    videos = response.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No se encontraron videos de stock para: {keywords!r}")

    video_files = sorted(videos[0]["video_files"], key=lambda f: abs((f.get("width") or 0) - 1920))
    file_url = video_files[0]["link"]

    video_response = requests.get(file_url, timeout=60)
    video_response.raise_for_status()
    out_path.write_bytes(video_response.content)
    return out_path


def fetch_clips_for_scenes(scenes: list[dict], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    clip_paths = []
    for i, scene in enumerate(scenes):
        photo_subject = (scene.get("photo_subject") or "").strip()
        if photo_subject:
            photo_path = real_photos.fetch_portrait(photo_subject, out_dir / f"clip_{i:02d}.jpg")
            if photo_path is not None:
                clip_paths.append(photo_path)
                continue

        out_path = out_dir / f"clip_{i:02d}.mp4"
        fetch_clip_for_scene(scene["visual_keywords"], out_path)
        clip_paths.append(out_path)
    return clip_paths
