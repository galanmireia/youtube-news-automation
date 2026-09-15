import logging
import re
import unicodedata
from pathlib import Path

import requests

from .config import CHANNEL_NAME

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://es.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://es.wikipedia.org/api/rest_v1/page/summary/{title}"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

# Wikimedia's API policy requires a descriptive User-Agent identifying the
# application (https://meta.wikimedia.org/wiki/User-Agent_policy) - requests
# without one (the default is a generic "python-requests/x.y") can be
# rate-limited or rejected outright, which would silently look exactly like
# "no photo exists" to every caller here.
_HEADERS = {"User-Agent": f"{CHANNEL_NAME}NewsBot/1.0 (automated video generation; contact via YouTube channel)"}


# The channel reports Spanish news, so where an institution exists under the
# same name in several countries, Spain's is the one meant unless the request
# says otherwise. Wikipedia disambiguates exactly this way: "Fiscalia General
# del Estado (Espana)" next to "Fiscalia General del Estado (Ecuador)".
_HOME_QUALIFIERS = {"espana", "espanol", "espanola"}


def _fold(text: str) -> str:
    """Accent- and case-insensitive comparison form, so "Espana" matches the
    "(España)" a Wikipedia title actually carries."""
    stripped = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c))


def _qualifier(title: str) -> str:
    """The disambiguator Wikipedia puts in trailing parentheses, folded.
    Empty for a plain title."""
    match = re.search(r"\(([^()]*)\)\s*$", title)
    return _fold(match.group(1)) if match else ""


def _rank_candidates(name: str, titles: list[str]) -> list[str]:
    """Reorders search results by how well they answer what was asked.

    Wikipedia's search ranks by relevance across the whole encyclopedia,
    which is not the same question. Asked for "Fiscalia General del Estado"
    in a story about Spain, it put Ecuador's article first and that is the
    image that reached a video - the same class of mistake as the Chinese
    flag in an earlier one.

    Sorting is stable, so search relevance still decides within a tier."""
    asked = _fold(name)

    def tier(title: str) -> int:
        qualifier = _qualifier(title)
        if _fold(title) == asked:
            return 0  # exactly the article asked for
        if qualifier and qualifier in asked:
            return 1  # the request named this country/qualifier itself
        if not qualifier:
            return 2  # the plain article, i.e. the primary meaning
        if qualifier in _HOME_QUALIFIERS:
            return 3  # Spain, the channel's default
        return 4  # some other country's namesake

    return sorted(titles, key=tier)


# Six rather than three: ranking below only helps if the right article is in
# the list at all, and they all come back from the same single request.
def _search_candidate_titles(name: str, limit: int = 6) -> list[str]:
    """Uses Wikipedia's real full-text search (the same engine behind the
    site's own search box) ranked by relevance/popularity, instead of a
    prefix-only match - a plain/common name like "Oscar Lopez" can otherwise
    resolve to the wrong person or a disambiguation page with no photo."""
    try:
        response = requests.get(
            WIKIPEDIA_API_URL,
            params={"action": "query", "list": "search", "srsearch": name, "srlimit": limit, "format": "json"},
            headers=_HEADERS,
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
            headers=_HEADERS,
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


def _download(url: str, out_path: Path) -> bool:
    try:
        image_response = requests.get(url, headers=_HEADERS, timeout=30)
        image_response.raise_for_status()
        out_path.write_bytes(image_response.content)
        return True
    except requests.RequestException:
        return False


def _fetch_summary_photo(title: str, out_path: Path, exclude_urls: set[str]) -> tuple[Path, str] | None:
    try:
        response = requests.get(
            WIKIPEDIA_SUMMARY_URL.format(title=title.replace(" ", "_")), headers=_HEADERS, timeout=15
        )
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
        if not thumbnail or thumbnail in exclude_urls:
            return None

        if not _download(thumbnail, out_path):
            return None
        return out_path, thumbnail
    except (requests.RequestException, ValueError):
        return None


def _commons_search_photo(name: str, out_path: Path, exclude_urls: set[str]) -> tuple[Path, str] | None:
    """Last resort: search Wikimedia Commons itself (the free-media library
    behind every Wikipedia, with far more photos per subject than any single
    Wikipedia article shows) instead of a specific Wikipedia page's lead
    image. Useful when a subject has no Wikipedia article/infobox photo at
    all but does have free-licensed photos on Commons (many buildings,
    landmarks and organizations do), and as a source of a SECOND, different
    picture of a subject already shown earlier in the same video."""
    try:
        response = requests.get(
            COMMONS_API_URL,
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": name,
                "gsrnamespace": 6,  # File: namespace only
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 1200,
                "format": "json",
            },
            headers=_HEADERS,
            timeout=15,
        )
        if response.status_code != 200:
            return None
        pages = response.json().get("query", {}).get("pages", {})
        for page in sorted(pages.values(), key=lambda p: p.get("index", 0)):
            title = page.get("title", "?")
            imageinfo = page.get("imageinfo") or [{}]
            source = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
            if not source or source in exclude_urls:
                continue
            if _download(source, out_path):
                logger.info("fetch_portrait(%r): imagen de Commons via archivo %r", name, title)
                return out_path, source
        return None
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


def fetch_portrait(person_name: str, out_path: Path, exclude_urls: set[str] | None = None) -> tuple[Path, str] | None:
    """Looks up a real public figure's (or a named place/institution's)
    photo, preferring Wikipedia (free-licensed infobox images, trying the
    top few search results in order, skipping disambiguation pages and
    articles with no image), then falling back to a direct Wikimedia
    Commons search if no Wikipedia article had a usable photo.

    Returns the path plus the image's URL, so callers can remember what they
    already used: an entity named in several scenes would otherwise show the
    exact same picture every time. Anything in exclude_urls is skipped, so a
    repeat mention gets a different picture of the same subject where one
    exists. Returns None if nothing new works at all, letting callers fall
    back to stock footage rather than repeating themselves."""
    exclude = exclude_urls or set()
    candidates = _rank_candidates(person_name, _search_candidate_titles(person_name)) or [person_name]
    for title in candidates:
        result = _fetch_summary_photo(title, out_path, exclude)
        if result is not None:
            # A generic Commons file-search match (below) is far more prone
            # to picking an unrelated file for a short/ambiguous name (e.g.
            # "Partido Popular" matching some unrelated icon) than a
            # Wikipedia article match is - log which article actually
            # supplied the image so a wrong-looking result can be diagnosed
            # from logs instead of guessed at.
            logger.info("fetch_portrait(%r): imagen del articulo de Wikipedia %r", person_name, title)
            return result
    return _commons_search_photo(person_name, out_path, exclude)
