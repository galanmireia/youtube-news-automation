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


# The catalogue, ordered: the picker takes the first unused entry, so the
# strongest cases come first.
#
# Every entry is a case with the three things the script structure needs. A
# PERSON with a name, because "el hundimiento del Costa Concordia" is a
# subject and "el capitan que abandono el barco" is a story. A TECHNICAL
# CAUSE that can be explained, which is what separates this from a channel
# that only tells you something bad happened. And a RESOLVED ending - a
# sentence, a bankruptcy, a fugitive, a company that no longer exists -
# because the ending is the reason anybody stays to the end, and because a
# case still being argued in court is one the channel must not build a story
# on.
#
# The subject is computing rather than engineering, and the reason is
# measured. In Spanish, "naufragio documental" has a median of 74 views;
# the same format on technology reaches a different order of magnitude -
# 11.3M on Cambridge Analytica, 6.7M on Snowden, 4.2M on the boy who hacked
# NASA - and technology pays better per view than history does. It is also
# the one subject where this channel has an advantage that cannot be copied:
# somebody who can tell whether the technical explanation is right.
#
# These are SEARCH TERMS, not exact article titles. They resolve through
# Wikipedia's own search, so an entry phrased differently from the real
# article still lands on it - written without being able to reach Wikipedia
# to check them, which is exactly why nothing here assumes an exact match.
# Entries that resolve to nothing are named in the log rather than counted.
CATALOGUE = [
    # Intrusiones con nombre y apellidos
    "Jonathan James hacker NASA",
    "Mirai botnet",
    "WannaCry",
    "Marcus Hutchins",
    "Kevin Mitnick",
    "Gusano Morris",
    "Stuxnet",
    "Gary McKinnon",
    "Albert Gonzalez hacker",
    "Grupo Lazarus",
    "Robo al Banco de Bangladés",
    "Carbanak",
    "Hackeo a Sony Pictures Entertainment",
    "Ciberataque a Colonial Pipeline",
    "Ataque a SolarWinds",
    "Operación Aurora",
    "Ciberataque al SEPE",
    "Ataque DDoS a Dyn",
    # Fraudes tecnologicos
    "Theranos",
    "Elizabeth Holmes",
    "OneCoin",
    "Ruja Ignatova",
    "Quiebra de FTX",
    "Sam Bankman-Fried",
    "Mt. Gox",
    "Caso Wirecard",
    "BitConnect",
    "QuadrigaCX",
    "Terra Luna criptomoneda",
    "Nikola Corporation fraude",
    # Filtraciones y vigilancia
    "Edward Snowden",
    "Escándalo de Cambridge Analytica",
    "Cablegate",
    "Chelsea Manning",
    "Papeles de Panamá",
    "Pegasus software espía",
    "Filtración de Ashley Madison",
    "Brecha de datos de Equifax",
    "Filtración de datos de Yahoo",
    # Software que fallo y costo caro
    "Therac-25",
    "Vuelo 501 del Ariane 5",
    "Mars Climate Orbiter",
    "Knight Capital",
    "Boeing 737 MAX MCAS",
    "Heartbleed",
    "Log4Shell",
    "Apagón informático de CrowdStrike",
    "Efecto 2000",
    "Apagón del noreste de 2003",
    # Mercado negro digital
    "Silk Road mercado negro",
    "Ross Ulbricht",
    "AlphaBay",
    # Imperios que se cayeron
    "Napster",
    "Declive de Nokia",
    "Quiebra de Blockbuster",
    "Quiebra de Kodak",
    "Declive de BlackBerry",
    "MySpace red social",
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


def fetch_topic_by_term(term: str) -> dict | None:
    """One named case, whether or not it has been made before, in the same
    shape the catalogue returns. This is what lets the same story be remade
    after a change to the script prompt: comparing two tellings of the Costa
    Concordia is the only way to tell whether a structural change to the
    writing helped, and the ordinary path would skip it as already processed.
    The term is resolved through Wikipedia's search like any catalogue entry,
    so a rough name still finds its article."""
    title = _resolve(term)
    if title is None:
        logger.warning("No encuentro ningun articulo de Wikipedia para %r.", term)
        return None
    texto = _extract(title)
    if not texto:
        logger.warning("El articulo %r no tiene texto utilizable.", title)
        return None
    logger.info("Tema forzado: %r -> articulo %r", term, title)
    return {
        "title": title,
        "summary": texto,
        "link": _article_url(title),
        "published": "",
        "source_name": "Wikipedia",
    }


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
