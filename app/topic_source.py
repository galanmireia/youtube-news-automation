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

from .config import CHANNEL_NAME, WIKI_LANG
from .storage import is_source_processed

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = f"https://{WIKI_LANG}.wikipedia.org/w/api.php"
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
    # Los titulos son los de la Wikipedia EN INGLES, que es la que se lee: la
    # mitad de estos casos no tiene articulo en espanol y los que lo tienen son
    # mucho mas cortos. Comprobables con /catalogo, que es de donde salieron -
    # escritos de memoria fallan en silencio, resolviendo a otro articulo.
    #
    # Criterio para entrar aqui, y es duro: el caso tiene que estar DOCUMENTADO
    # EN WIKIPEDIA. Los misterios de internet abundan en foros y en videos de
    # otros, y de ahi no se puede sacar nada - ni por derechos ni por fiabilidad.
    # Un caso sin articulo solido es un guion que se inventa el relleno.

    # Criptogramas y acertijos sin resolver
    "Cicada 3301",
    "Kryptos",
    "Voynich manuscript",
    "Beale ciphers",
    "Tamam Shud case",
    "Phaistos Disc",
    "Publius Enigma",
    "Zodiac Killer",

    # Emisiones y señales que nadie explica
    "Webdriver Torso",
    "Wow! signal",
    "UVB-76",
    "Max Headroom signal hijacking",
    "Numbers station",
    "Bloop",
    "Lincolnshire Poacher (numbers station)",

    # Leyendas que salieron de internet y tuvieron consecuencias reales
    "Slender Man",
    "Slender Man stabbing",
    "Momo Challenge hoax",
    "Blue Whale Challenge",
    "Creepypasta",
    "Polybius (urban legend)",
    "Pizzagate conspiracy theory",

    # Identidades ocultas
    "Satoshi Nakamoto",
    "Banksy",
    "D. B. Cooper",
    "QAnon",

    # Desapariciones y casos con rastro digital
    "Death of Elisa Lam",
    "Disappearance of Maura Murray",
    "Disappearance of Lars Mittank",
    "Malaysia Airlines Flight 370",

    # Rincones oscuros de la red
    "Silk Road (marketplace)",
    "Ross Ulbricht",
    "Dark web",
    "Tor (network)",
    "Anonymous (hacker group)",
    "LulzSec",
    "4chan",
    "Ashley Madison data breach",

    # Fraudes y enganos nacidos en la red
    "Dead Internet theory",
    "Fyre Festival",
    "OneCoin",
    "Theranos",
    "Elizabeth Holmes",
    "Advance-fee scam",

    # Desastres informaticos que el publico conoce
    "Morris worm",
    "WannaCry ransomware attack",
    "Stuxnet",
    "Mirai (malware)",
    "ILOVEYOU",
    "Kevin Mitnick",
    "2024 CrowdStrike-related IT outages",

    # Vigilancia y filtraciones
    "Edward Snowden",
    "Cambridge Analytica",
    "WikiLeaks",
    "Room 641A",
    "PRISM",
]



def _resolve(term: str) -> str | None:
    """The real article title for a search term, or None if Wikipedia has no
    article for it. Searching rather than assuming means an entry written from
    memory still finds its article."""
    try:
        from . import research
        response = research.peticion(
            WIKIPEDIA_API_URL,
            {"action": "query", "list": "search", "srsearch": term, "srlimit": 1,
             "format": "json"},
            timeout=20,
        )
        if response is None or response.status_code != 200:
            return None
        results = response.json().get("query", {}).get("search", [])
        return results[0]["title"] if results else None
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None


def _extract(title: str) -> str:
    """The article's plain text, trimmed to what a script actually needs.

    Delegates to research._extract instead of asking the API itself, and that
    is the point: this had its own copy of the same call, with the same
    silent except around it, so the day the extracts extension returned
    nothing BOTH went empty and neither said why. One route, one fallback,
    one place to fix."""
    from . import research
    return research._extract(WIKI_LANG, title, _EXTRACT_CHARS)

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
