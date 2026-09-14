from pathlib import Path

import requests

WIKIPEDIA_API_URL = "https://es.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://es.wikipedia.org/api/rest_v1/page/summary/{title}"


def _search_candidate_titles(name: str, limit: int = 3) -> list[str]:
    """Uses Wikipedia's real full-text search (the same engine behind the
    site's own search box) ranked by relevance/popularity, instead of a
    prefix-only match - a plain/common name like "Oscar Lopez" can otherwise
    resolve to the wrong person or a disambiguation page with no photo."""
    try:
        response = requests.get(
            WIKIPEDIA_API_URL,
            params={"action": "query", "list": "search", "srsearch": name, "srlimit": limit, "format": "json"},
            timeout=15,
        )
        if response.status_code != 200:
            return []
        return [result["title"] for result in response.json().get("query", {}).get("search", [])]
    except (requests.RequestException, KeyError, ValueError):
        return []


def _fetch_summary_photo(title: str, out_path: Path) -> Path | None:
    try:
        response = requests.get(WIKIPEDIA_SUMMARY_URL.format(title=title.replace(" ", "_")), timeout=15)
        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("type") == "disambiguation":
            return None

        thumbnail = data.get("thumbnail", {}).get("source") or data.get("originalimage", {}).get("source")
        if not thumbnail:
            return None

        image_response = requests.get(thumbnail, timeout=30)
        image_response.raise_for_status()
        out_path.write_bytes(image_response.content)
        return out_path
    except requests.RequestException:
        return None


def fetch_portrait(person_name: str, out_path: Path) -> Path | None:
    """Looks up a real public figure's (or a named place/institution's)
    photo on Wikipedia (free-licensed infobox images). Tries the top few
    search results in order - skipping disambiguation pages and articles
    with no image - until one yields a real photo. Returns None if nothing
    works, so callers can fall back to stock footage."""
    candidates = _search_candidate_titles(person_name) or [person_name]
    for title in candidates:
        photo_path = _fetch_summary_photo(title, out_path)
        if photo_path is not None:
            return photo_path
    return None
