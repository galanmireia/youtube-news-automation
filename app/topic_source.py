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
    # Misterios de internet, que es donde estan los numeros.
    #
    # Medido sobre 1.494 videos y 1.278 canales: de cuarenta y dos nichos, el
    # que sostiene canales jovenes en ingles con mas visitas por video es este
    # - veinte canales con menos de dieciocho meses y una mediana de 72.522
    # visitas por video, con varios por encima del millon. La informatica pura
    # NO lo hace: su mediana es 3.321, y el unico video que revento (5,6
    # millones sobre virus) tiene debajo a otro canal con el mismo tema, el
    # mismo formato y 43 visitas.
    #
    # Criterio para entrar aqui, y es duro: el caso tiene que estar DOCUMENTADO
    # EN WIKIPEDIA. Los misterios de internet abundan en foros y en videos de
    # otros, y de ahi no se puede sacar nada - ni por derechos ni por fiabilidad.
    # Un caso sin articulo solido es un guion que se inventa el relleno.

    # Criptogramas y acertijos sin resolver
    "Cicada 3301",
    "Kryptos",
    "Manuscrito Voynich",
    "Codigo Beale",
    "Taman Shud",
    "Disco de Festos",
    "Publius Enigma",
    "Zodiac Killer cifrado",

    # Emisiones y señales que nadie explica
    "Webdriver Torso",
    "Señal Wow!",
    "UVB-76",
    "Incidente de Max Headroom",
    "Numbers station",
    "Bloop",
    "Lincolnshire Poacher",

    # Leyendas que salieron de internet y tuvieron consecuencias reales
    "Slender Man",
    "Apuñalamiento de Slender Man",
    "Momo Challenge",
    "Reto de la ballena azul",
    "Creepypasta",
    "Polybius videojuego",
    "Pizzagate",

    # Identidades ocultas
    "Satoshi Nakamoto",
    "Banksy",
    "D. B. Cooper",
    "Q (QAnon)",
    "Bitcoin creador",

    # Desapariciones y casos con rastro digital
    "Elisa Lam",
    "Desaparicion de Maura Murray",
    "Caso de Lars Mittank",
    "Hombre de Somerton",
    "Vuelo 370 de Malaysia Airlines",

    # Rincones oscuros de la red
    "Silk Road (mercado negro)",
    "Ross Ulbricht",
    "Deep web",
    "Red Tor",
    "Anonymous (colectivo)",
    "LulzSec",
    "4chan",
    "Ashley Madison filtracion",

    # Fraudes y engaños nacidos en la red
    "Teoria del internet muerto",
    "Fyre Festival",
    "OneCoin",
    "Theranos",
    "Elizabeth Holmes",
    "Estafa nigeriana",

    # Desastres informaticos que el publico conoce
    "Gusano Morris",
    "WannaCry",
    "Stuxnet",
    "Mirai botnet",
    "ILOVEYOU",
    "Kevin Mitnick",
    "Caida de CrowdStrike de 2024",

    # Vigilancia y filtraciones
    "Edward Snowden",
    "Cambridge Analytica",
    "WikiLeaks",
    "Room 641A",
    "PRISM (programa de vigilancia)",
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
