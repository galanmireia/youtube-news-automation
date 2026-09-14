from pathlib import Path

import requests

WIKIPEDIA_SUMMARY_URL = "https://es.wikipedia.org/api/rest_v1/page/summary/{title}"


def fetch_portrait(person_name: str, out_path: Path) -> Path | None:
    """Looks up a real public figure's photo on Wikipedia (free-licensed
    infobox images). Returns None if there's no article, no image, or the
    request fails for any reason, so callers can fall back to stock footage."""
    try:
        response = requests.get(
            WIKIPEDIA_SUMMARY_URL.format(title=person_name.strip().replace(" ", "_")), timeout=15
        )
        if response.status_code != 200:
            return None

        data = response.json()
        thumbnail = data.get("thumbnail", {}).get("source") or data.get("originalimage", {}).get("source")
        if not thumbnail:
            return None

        image_response = requests.get(thumbnail, timeout=30)
        image_response.raise_for_status()
        out_path.write_bytes(image_response.content)
        return out_path
    except requests.RequestException:
        return None
