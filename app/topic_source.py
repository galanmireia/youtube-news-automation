"""Where a catastrophe/engineering video gets its subject and its facts.

This replaces the RSS feed for the new format. A news channel has stories
pushed at it; this one has to pull them from a catalogue, because an engineering
disaster does not arrive in a feed on the morning it becomes interesting.

Two things make Wikipedia the right source rather than a convenient one. The
facts come from an article instead of from the model's memory, which is where
invented figures come from - and in a format whose whole appeal is real numbers,
an invented one is fatal. And Commons has genuinely good free images of ships,
aircraft, bridges, plants and diagrams, which is the single thing our picture
pipeline is best at and the thing daily news never gave it.

Entries below are SEARCH TERMS, not exact article titles. They are resolved
through Wikipedia's own search, so an entry phrased slightly differently from
the real article still lands on it - written without being able to reach
Wikipedia to check each one, which is precisely why nothing here assumes an
exact match.
"""

import logging

import requests

from .config import CHANNEL_NAME
from .storage import is_source_processed

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://es.wikipedia.org/w/api.php"
_HEADERS = {
    "User-Agent": f"{CHANNEL_NAME}Bot/1.0 (automated video generation; contact via YouTube channel)"
}

# How much of the article to carry into the script. The lead alone is too thin
# for a five-minute video; the whole article is mostly footnotes and legacy
# sections. The first several thousand characters cover the build-up, the event
# and the causes, which is the shape of the story we tell.
_EXTRACT_CHARS = 9000


# The catalogue. Mixed deliberately: failures are the hook, but a channel that
# only ever shows things breaking gets monotonous, so feats of engineering are
# in here too - the format is "how something huge was built or came apart".
CATALOGUE = [
    # Mar
    "Hundimiento del RMS Titanic",
    "Naufragio del Costa Concordia",
    "Desastre del Prestige",
    "MS Estonia naufragio",
    "Hundimiento del Doña Paz",
    "Hundimiento del ferry Sewol",
    "Submarino K-141 Kursk",
    "Sumergible Titan implosión",
    "Desastre de Piper Alpha",
    "Marea negra del Exxon Valdez",
    "Explosión de la Deepwater Horizon",
    # Aire
    "Accidente aéreo de Los Rodeos",
    "Vuelo 123 de Japan Airlines",
    "Vuelo 5022 de Spanair",
    "Vuelo 4590 de Air France Concorde",
    "Vuelo 191 de American Airlines",
    "Vuelo 592 de ValuJet",
    "Accidentes del Boeing 737 MAX",
    "Dirigible Hindenburg",
    "Vuelo 143 de Air Canada planeador de Gimli",
    # Espacio
    "Accidente del transbordador espacial Challenger",
    "Accidente del transbordador espacial Columbia",
    "Incendio del Apolo 1",
    "Apolo 13",
    "Mars Climate Orbiter",
    # Nuclear e industrial
    "Accidente de Chernóbil",
    "Accidente nuclear de Fukushima I",
    "Accidente de Three Mile Island",
    "Desastre de Bhopal",
    "Explosión de Texas City",
    "Explosión del puerto de Beirut de 2020",
    "Explosiones de Tianjin de 2015",
    "Explosión de Halifax",
    "Desastre de Seveso",
    "Síndrome del aceite tóxico colza",
    # Presas y agua
    "Desastre de Vajont",
    "Rotura de la presa de Banqiao",
    "Rotura de la presa de Malpasset",
    "Pantanada de Tous",
    "Desastre de Ribadelago",
    "Desastre de Aznalcóllar",
    # Estructuras
    "Puente Morandi de Génova",
    "Puente de Tacoma Narrows",
    "Colapso de las pasarelas del hotel Hyatt Regency",
    "Incendio de la Torre Grenfell",
    "Incendio del edificio Windsor",
    "Derrumbe del Rana Plaza",
    "Incendio del túnel del Mont Blanc",
    "Torre inclinada de Pisa",
    # Tierra y minas
    "Desastre de Aberfan",
    "Accidente de la mina San José rescate",
    "Terremoto de Lisboa de 1755",
    # Ingenieria que si salio bien
    "Construcción del Canal de Panamá",
    "Eurotúnel del Canal de la Mancha",
    "Presa Hoover",
    "Construcción de la Torre Eiffel",
    "Traslado de los templos de Abu Simbel",
    "Delta Works de los Países Bajos",
]


def _resolve(term: str) -> str | None:
    """The real article title for a search term, or None if Wikipedia has no
    article for it. Searching rather than assuming means an entry written from
    memory still finds its article."""
    try:
        response = requests.get(
            WIKIPEDIA_API_URL,
            params={"action": "query", "list": "search", "srsearch": term, "srlimit": 1, "format": "json"},
            headers=_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
        return results[0]["title"] if results else None
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None


def _extract(title: str) -> str:
    """The article's plain text, trimmed to what a script actually needs."""
    try:
        response = requests.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "exsectionformat": "plain",
                "titles": title,
                "format": "json",
                "redirects": 1,
            },
            headers=_HEADERS,
            timeout=25,
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            texto = (page.get("extract") or "").strip()
            if texto:
                return texto[:_EXTRACT_CHARS]
    except (requests.RequestException, KeyError, ValueError):
        pass
    return ""


def _article_url(title: str) -> str:
    return "https://es.wikipedia.org/wiki/" + title.replace(" ", "_")


def fetch_candidate_topics(limit: int = 5) -> list[dict]:
    """Up to `limit` unused cases, in the same shape the RSS source returned,
    so everything downstream is unchanged.

    Walks the catalogue in order and stops as soon as it has enough, so one
    run costs a couple of Wikipedia requests rather than sixty."""
    candidates: list[dict] = []
    sin_articulo: list[str] = []

    for term in CATALOGUE:
        if len(candidates) >= limit:
            break
        title = _resolve(term)
        if title is None:
            sin_articulo.append(term)
            continue
        url = _article_url(title)
        if is_source_processed(url):
            continue
        texto = _extract(title)
        if not texto:
            sin_articulo.append(term)
            continue
        candidates.append(
            {
                "title": title,
                "summary": texto,
                "link": url,
                "published": "",
                "source_name": "Wikipedia",
            }
        )

    if sin_articulo:
        # Named rather than counted: the catalogue was written without being
        # able to reach Wikipedia, so the entries that miss are worth knowing.
        logger.warning("Temas sin articulo utilizable en Wikipedia: %s", ", ".join(sin_articulo))
    logger.info("Temas disponibles: %s de un catalogo de %s.", len(candidates), len(CATALOGUE))
    return candidates
