from pathlib import Path

import requests

WIKIPEDIA_OPENSEARCH_URL = "https://es.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://es.wikipedia.org/api/rest_v1/page/summary/{title}"


def _resolve_article_title(person_name: str) -> str | None:
    """Person names from the script rarely match a Wikipedia article's exact
    title (accents, disambiguation suffixes, middle names). Wikipedia's own
    search resolves that the same way the site's search box does, instead of
    guessing by replacing spaces with underscores."""
    try:
        response = requests.get(
            WIKIPEDIA_OPENSEARCH_URL,
            params={
                "action": "opensearch",
                "search": person_name,
                "limit": 1,
                "namespace": 0,
                "format": "json",
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        titles = response.json()[1]
        return titles[0] if titles else None
    except (requests.RequestException, IndexError, ValueError):
        return None


def fetch_portrait(person_name: str, out_path: Path) -> Path | None:
    """Looks up a real public figure's photo on Wikipedia (free-licensed
    infobox images). Returns None if there's no article, no image, or the
    request fails for any reason, so callers can fall back to stock footage."""
    title = _resolve_article_title(person_name) or person_name.strip().replace(" ", "_")
    try:
        response = requests.get(WIKIPEDIA_SUMMARY_URL.format(title=title), timeout=15)
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
