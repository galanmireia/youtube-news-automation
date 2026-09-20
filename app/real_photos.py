import logging
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote

import requests

from .config import CHANNEL_NAME, WIKI_LANG

logger = logging.getLogger(__name__)

# Spanish first - it is the channel's language, and its article is what the
# descriptors and titles should come from. English second, because it is more
# than three times the size and carries far more free images of exactly what
# this channel is about: ships, aircraft, bridges, plants and the disasters
# that befell them. Plenty of engineering subjects have an article, or a
# photograph, in only one of the two. Commons, searched last, is shared by
# both - but WHICH image an article puts at the top is decided per language,
# so asking two wikis is not the same question asked twice.
# The channel's language first, then the other, because which photo an
# article puts at the top is decided per language and the article in the
# channel's language is the one whose naming the script used.
WIKI_LANGS = (WIKI_LANG,) + tuple(l for l in ("en", "es") if l != WIKI_LANG)


def _api_url(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def _summary_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"


WIKIPEDIA_API_URL = _api_url(WIKI_LANG)
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

# Wikimedia's API policy requires a descriptive User-Agent identifying the
# application (https://meta.wikimedia.org/wiki/User-Agent_policy) - requests
# without one (the default is a generic "python-requests/x.y") can be
# rate-limited or rejected outright, which would silently look exactly like
# "no photo exists" to every caller here.
_HEADERS = {"User-Agent": f"{CHANNEL_NAME}NewsBot/1.0 (automated video generation; contact via YouTube channel)"}


# Where an institution exists under the same name in several countries,
# this is the one meant unless the request says otherwise. Wikipedia
# disambiguates exactly this way: "Federal Bureau of Investigation" next to
# the national police of somewhere else. This catalogue is overwhelmingly US
# cases, so that is the default - but it is a DEFAULT, not a rule: the script
# is told to disambiguate the country itself when the case is not American.
_HOME_QUALIFIERS = {"united states", "u.s.", "us", "american", "usa"}


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
def _search_candidate_titles(name: str, lang: str = WIKI_LANG, limit: int = 6) -> list[str]:
    """Uses Wikipedia's real full-text search (the same engine behind the
    site's own search box) ranked by relevance/popularity, instead of a
    prefix-only match - a plain/common name like "Oscar Lopez" can otherwise
    resolve to the wrong person or a disambiguation page with no photo."""
    try:
        response = requests.get(
            _api_url(lang),
            params={"action": "query", "list": "search", "srsearch": name, "srlimit": limit, "format": "json"},
            headers=_HEADERS,
            timeout=15,
        )
        if response.status_code != 200:
            return []
        return [result["title"] for result in response.json().get("query", {}).get("search", [])]
    except (requests.RequestException, KeyError, ValueError):
        return []


def _pageimages_thumbnail_url(title: str, lang: str = WIKI_LANG) -> str | None:
    """Fallback for pages where the REST summary endpoint doesn't surface a
    lead image (common for institutions/buildings/organizations) even though
    the article does have one. action=query&prop=pageimages is a separate,
    more permissive MediaWiki API that often finds it anyway."""
    try:
        response = requests.get(
            _api_url(lang),
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


# What Wikipedia puts at the top of an article is not always a photograph.
# For a country it is the flag; for a public body, the logo; for a region, a
# locator map. Those are all correct answers to "illustrate this article" and
# all useless as a shot in a video: they carry no information the narration
# does not already give, they are visually dead, and a logo on screen is
# something this channel does not do. They are recognisable from the file
# name, which Wikimedia keeps descriptive.
#
# The strongest single signal is the format. A flag, a coat of arms, a logo
# and a locator map are vector drawings; a photograph never is. The REST API
# hands back a rasterised PNG of the SVG, so the ".svg" survives in the path
# of the thumbnail URL and is still there to be seen.
#
# The name patterns are anchored at word boundaries on purpose: a bare
# "logo" substring also appears inside "geologo", and "map" inside
# "Mapuche". Rejecting a real photograph is worse than letting a symbol
# through, because the symbol has a fallback (stock footage or an AI
# illustration) and the photograph does not.
_SYMBOL_PATTERNS = (
    r"\.svg",
    r"(^|[/_\- ])flags?([_\- ]|$)",
    r"(^|[/_\- ])banderas?([_\- ]|$)",
    r"coat[_\- ]of[_\- ]arms",
    r"(^|[/_\- ])escudo([_\- ]|$)",
    r"(^|[/_\- ])emblem",
    r"seal[_\- ]of[_\- ]",
    r"(^|[/_\- ])logos?([_\- ]|$)",
    r"logotipo",
    r"wordmark",
    r"location[_\- ]map",
    r"(^|[/_\- ])locator([_\- ]|$)",
    r"(^|[/_\- ])map[_\- ]of([_\- ]|$)",
    r"(^|[/_\- ])mapa[_\- ]de([_\- ]|$)",
    r"orthographic",
)

_SYMBOL_RE = re.compile("|".join(_SYMBOL_PATTERNS), re.IGNORECASE)


def _is_symbol_not_photograph(url: str) -> bool:
    """True for a flag, coat of arms, emblem, logo or locator map - the
    things Wikipedia leads with when a subject is too abstract to photograph."""
    return bool(_SYMBOL_RE.search(unquote(url)))


# A subject with no single photograph of it. Asked to illustrate "China",
# Wikipedia can only offer a flag, a map or a national emblem, because there
# is no photograph of a country - and the pipeline will happily put twelve
# seconds of it on screen while the narration talks about a shipyard. These
# are never the subject of a story on this channel; they are the place a
# subject happens to be, which the narration already says out loud.
#
# The list is deliberately only the over-broad names. A city, a coastline, a
# ship or a plant is a real place with real photographs and must keep working
# - "Costa de la Muerte" gives a photograph of a cape, and that is a good
# shot.
_TOO_BROAD_FOR_A_PHOTO = frozenset(
    _fold(name)
    for name in (
        # Continents, oceans and the broad regions a script name-drops.
        "Europa", "Asia", "Africa", "America", "America del Norte",
        "America del Sur", "Norteamerica", "Sudamerica", "Latinoamerica",
        "America Latina", "Centroamerica", "Oceania", "Antartida",
        "Oriente Medio", "Oriente Proximo", "Union Europea", "OTAN", "ONU",
        "Naciones Unidas", "Occidente", "Escandinavia", "los Balcanes",
        "Oceano Atlantico", "Oceano Pacifico", "Oceano Indico",
        "Oceano Artico", "Mar Mediterraneo", "Mar del Norte", "Mar Baltico",
        "Mar Negro", "Mar Caribe", "el mundo", "la Tierra",
        # Countries. A country is a flag, never a photograph.
        "Afganistan", "Albania", "Alemania", "Andorra", "Angola",
        "Arabia Saudi", "Arabia Saudita", "Argelia", "Argentina", "Armenia",
        "Australia", "Austria", "Azerbaiyan", "Bahamas", "Banglades",
        "Barein", "Belgica", "Belice", "Benin", "Bielorrusia", "Bolivia",
        "Bosnia y Herzegovina", "Botsuana", "Brasil", "Brunei", "Bulgaria",
        "Burkina Faso", "Burundi", "Butan", "Cabo Verde", "Camboya",
        "Camerun", "Canada", "Catar", "Chad", "Chile", "China", "Chipre",
        "Colombia", "Comoras", "Corea del Norte", "Corea del Sur",
        "Costa de Marfil", "Costa Rica", "Croacia", "Cuba", "Dinamarca",
        "Ecuador", "Egipto", "El Salvador", "Emiratos Arabes Unidos",
        "Eritrea", "Eslovaquia", "Eslovenia", "Espana", "Estados Unidos",
        "Estonia", "Etiopia", "Filipinas", "Finlandia", "Fiyi", "Francia",
        "Gabon", "Gambia", "Georgia", "Ghana", "Grecia", "Guatemala",
        "Guinea", "Guinea Ecuatorial", "Guyana", "Haiti", "Honduras",
        "Hungria", "India", "Indonesia", "Irak", "Iran", "Irlanda",
        "Islandia", "Islas Marshall", "Israel", "Italia", "Jamaica",
        "Japon", "Jordania", "Kazajistan", "Kenia", "Kirguistan", "Kiribati",
        "Kosovo", "Kuwait", "Laos", "Lesoto", "Letonia", "Libano", "Liberia",
        "Libia", "Liechtenstein", "Lituania", "Luxemburgo", "Macedonia del Norte",
        "Madagascar", "Malasia", "Malaui", "Maldivas", "Mali", "Malta",
        "Marruecos", "Mauricio", "Mauritania", "Mexico", "Micronesia",
        "Moldavia", "Monaco", "Mongolia", "Montenegro", "Mozambique",
        "Myanmar", "Namibia", "Nauru", "Nepal", "Nicaragua", "Niger",
        "Nigeria", "Noruega", "Nueva Zelanda", "Oman", "Paises Bajos",
        "Pakistan", "Palaos", "Palestina", "Panama", "Papua Nueva Guinea",
        "Paraguay", "Peru", "Polonia", "Portugal", "Reino Unido",
        "Republica Checa", "Republica Centroafricana",
        "Republica Democratica del Congo", "Republica Dominicana",
        "Ruanda", "Rumania", "Rusia", "Samoa", "San Marino", "Santa Lucia",
        "Santo Tome y Principe", "Senegal", "Serbia", "Seychelles",
        "Sierra Leona", "Singapur", "Siria", "Somalia", "Sri Lanka",
        "Suazilandia", "Sudafrica", "Sudan", "Sudan del Sur", "Suecia",
        "Suiza", "Surinam", "Tailandia", "Tanzania", "Tayikistan",
        "Timor Oriental", "Togo", "Tonga", "Trinidad y Tobago", "Tunez",
        "Turkmenistan", "Turquia", "Tuvalu", "Ucrania", "Uganda", "Uruguay",
        "Uzbekistan", "Vanuatu", "Vaticano", "Venezuela", "Vietnam",
        "Yemen", "Yibuti", "Zambia", "Zimbabue",
    )
)


def _is_too_broad_to_photograph(name: str) -> bool:
    return _fold(name.strip()) in _TOO_BROAD_FOR_A_PHOTO


def _download(url: str, out_path: Path) -> bool:
    try:
        image_response = requests.get(url, headers=_HEADERS, timeout=30)
        image_response.raise_for_status()
        out_path.write_bytes(image_response.content)
        return True
    except requests.RequestException:
        return False


def _fetch_summary_photo(title: str, out_path: Path, exclude_urls: set[str], lang: str = WIKI_LANG) -> tuple[Path, str] | None:
    try:
        response = requests.get(
            _summary_url(lang, title.replace(" ", "_")), headers=_HEADERS, timeout=15
        )
        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("type") == "disambiguation":
            return None

        thumbnail = (
            data.get("thumbnail", {}).get("source")
            or data.get("originalimage", {}).get("source")
            or _pageimages_thumbnail_url(title, lang)
        )
        if not thumbnail or thumbnail in exclude_urls:
            return None
        if _is_symbol_not_photograph(thumbnail):
            logger.info(
                "  %r en %s: su imagen principal es un simbolo (%s), no una foto; se descarta.",
                title, lang, thumbnail.rsplit("/", 1)[-1],
            )
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
            if _is_symbol_not_photograph(source):
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
    if _is_too_broad_to_photograph(person_name):
        logger.info(
            "fetch_portrait(%r): sujeto demasiado amplio para tener una foto; "
            "la escena buscara imagen por otra via.",
            person_name,
        )
        return None
    for lang in WIKI_LANGS:
        candidates = _rank_candidates(
            person_name, _search_candidate_titles(person_name, lang)
        ) or [person_name]
        for title in candidates:
            result = _fetch_summary_photo(title, out_path, exclude, lang)
            if result is None:
                continue
            # A generic Commons file-search match (below) is far more prone
            # to picking an unrelated file for a short/ambiguous name (e.g.
            # "Partido Popular" matching some unrelated icon) than a
            # Wikipedia article match is - log which article actually
            # supplied the image, and in which language, so a wrong-looking
            # result can be diagnosed from logs instead of guessed at.
            logger.info(
                "fetch_portrait(%r): imagen del articulo %r de la Wikipedia en %s",
                person_name,
                title,
                lang,
            )
            return result
    return _commons_search_photo(person_name, out_path, exclude)


# ---------------------------------------------------------------------------
# Image credits.
#
# "FUENTE: WIKIPEDIA" burned into the corner of every frame was doing the
# worst of both jobs: it looked like a watermark and it is not attribution.
# Wikimedia images carry licences, and most of them require the AUTHOR and the
# LICENCE by name - which a one-word tag naming the website does not give. For
# a channel whose first requirement is that it stays monetisable, an invalid
# credit is a risk carried for nothing.
#
# So the credit leaves the picture and goes where video credits belong, in the
# description, with the author and licence the licence actually asks for.

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def _fichero_de_url(url: str) -> str:
    """The Commons file name inside an image URL, thumbnail or original."""
    partes = url.split("/")
    if "thumb" in partes:
        # .../thumb/a/ab/Foo.jpg/330px-Foo.jpg -> Foo.jpg
        i = partes.index("thumb")
        if len(partes) > i + 3:
            return unquote(partes[i + 3])
    return unquote(partes[-1]) if partes else ""


def _limpia(html: str) -> str:
    """Wikimedia returns the author as a fragment of HTML."""
    texto = re.sub(r"<[^>]+>", " ", html or "")
    return " ".join(texto.split()).strip()


def creditos_de(urls: list[str]) -> list[str]:
    """One credit line per image, in the order they were used.

    Asked at Commons rather than assumed: the author and the licence are
    per-file, and there is no way to know either from the URL. When the lookup
    fails the file name still goes in the list - naming the file is a weaker
    credit than naming its author, and far better than dropping it."""
    vistos: list[str] = []
    for url in urls:
        fichero = _fichero_de_url(url)
        if fichero and fichero not in vistos:
            vistos.append(fichero)
    if not vistos:
        return []

    metadatos: dict[str, tuple[str, str]] = {}
    # Fifty titles per request is the API's own limit, and one request for a
    # whole video beats one per image.
    for i in range(0, len(vistos), 50):
        lote = vistos[i:i + 50]
        try:
            r = requests.get(
                _COMMONS_API,
                params={
                    "action": "query", "format": "json", "prop": "imageinfo",
                    "iiprop": "extmetadata", "titles": "|".join(f"File:{f}" for f in lote),
                },
                headers=_HEADERS, timeout=25,
            )
            r.raise_for_status()
            paginas = r.json().get("query", {}).get("pages", {})
        except Exception:
            # Deliberately every exception, not just the network's. What is
            # being protected here is the ATTRIBUTION, and the fallback below
            # still names every file - so a failure in this lookup must cost
            # the author's name, never the credit itself. A credit that
            # vanishes because a request raised something unexpected is the
            # one outcome that carries a licensing risk.
            logger.warning(
                "No se han podido leer los creditos de %s imagenes; se acreditan por nombre de fichero.",
                len(lote), exc_info=True,
            )
            continue
        for pagina in paginas.values():
            titulo = (pagina.get("title") or "").removeprefix("File:")
            info = (pagina.get("imageinfo") or [{}])[0].get("extmetadata") or {}
            autor = _limpia(info.get("Artist", {}).get("value", ""))
            licencia = _limpia(info.get("LicenseShortName", {}).get("value", ""))
            if titulo:
                metadatos[titulo] = (autor, licencia)

    lineas = []
    for fichero in vistos:
        autor, licencia = metadatos.get(fichero, ("", ""))
        partes = [fichero.replace("_", " ")]
        if autor:
            partes.append(autor)
        if licencia:
            partes.append(licencia)
        lineas.append(" · ".join(partes) + " (Wikimedia Commons)")
    logger.info("Creditos de imagen resueltos: %s de %s.", len(metadatos), len(vistos))
    return lineas
