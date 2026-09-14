from pathlib import Path

import requests

WIKIPEDIA_API_URL = "https://es.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://es.wikipedia.org/api/rest_v1/page/summary/{title}"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"


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


def _pageimages_thumbnail_url(title: str) -> str | None:
    """Fallback for pages where the REST summary endpoint doesn't surface a
    lead image (common for institutions/buildings/organizations) even though
    the article does have one. action=query&prop=pageimages is a separate,
    more permissive MediaWiki API that often finds it anyway."""
    try:
        response = requests.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "piprop": "original",
                "redirects": 1,
                "format": "json",
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            source = page.get("original", {}).get("source")
            if source:
                return source
        return None
    except (requests.RequestException, KeyError, ValueError):
        return None


def _fetch_summary_photo(title: str, out_path: Path) -> Path | None:
    try:
        response = requests.get(WIKIPEDIA_SUMMARY_URL.format(title=title.replace(" ", "_")), timeout=15)
        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("type") == "disambiguation":
            return None

        thumbnail = (
            data.get("thumbnail", {}).get("source")
            or data.get("originalimage", {}).get("source")
            or _pageimages_thumbnail_url(title)
        )
        if not thumbnail:
            return None

        image_response = requests.get(thumbnail, timeout=30)
        image_response.raise_for_status()
        out_path.write_bytes(image_response.content)
        return out_path
    except requests.RequestException:
        return None


def _commons_search_photo(name: str, out_path: Path) -> Path | None:
    """Last resort: search Wikimedia Commons itself (the free-media library
    behind every Wikipedia, with far more photos per subject than any single
    Wikipedia article shows) instead of a specific Wikipedia page's lead
    image. Useful when a subject has no Wikipedia article/infobox photo at
    all but does have free-licensed photos on Commons (many buildings,
    landmarks and organizations do)."""
    try:
        response = requests.get(
            COMMONS_API_URL,
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": name,
                "gsrnamespace": 6,  # File: namespace only
                "gsrlimit": 1,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 1200,
                "format": "json",
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo") or [{}]
            source = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
            if source:
                image_response = requests.get(source, timeout=30)
                image_response.raise_for_status()
                out_path.write_bytes(image_response.content)
                return out_path
        return None
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


def fetch_portrait(person_name: str, out_path: Path) -> Path | None:
    """Looks up a real public figure's (or a named place/institution's)
    photo, preferring Wikipedia (free-licensed infobox images, trying the
    top few search results in order, skipping disambiguation pages and
    articles with no image), then falling back to a direct Wikimedia
    Commons search if no Wikipedia article had a usable photo. Returns None
    if nothing works at all, so callers can fall back to stock footage."""
    candidates = _search_candidate_titles(person_name) or [person_name]
    for title in candidates:
        photo_path = _fetch_summary_photo(title, out_path)
        if photo_path is not None:
            return photo_path
    return _commons_search_photo(person_name, out_path)
