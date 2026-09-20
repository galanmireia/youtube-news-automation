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
# El catalogo ya no es una lista escrita a mano: es el calendario de
# efemerides, ordenado por lo cerca que esta cada aniversario. Asi el tema que
# toca sale solo, sin que nadie tenga que acordarse de que el 26 de abril es
# Chernobil.
#
# De donde viene el cambio: los temas que no conocia nadie - Doña Paz, el
# Estonia, el Prestige - dieron 2, 17 y 9 visitas, y el documental del 11-S
# que estaba en tendencias hoy tenia 3.454.779. Mismo formato. Lo que cambia
# es cuanta gente conoce el suceso Y si hay algo que les recuerde buscarlo
# ahora, que casi siempre es el aniversario.
#
# El calendario PROPONE, no decide: un aniversario sin nadie buscandolo sigue
# siendo un mal video. Quien decide es la medicion de demanda del picker. Ella
# lo dijo mejor que yo con el festival de San Sebastian, que esta esta semana
# y no lo ve nadie.
#
# Se comprueba con /catalogo, que mira si cada titulo existe de verdad en
# Wikipedia. Esta escrito de memoria y hoy ya se demostro que eso falla.
from .efemerides import por_cercania


def _catalogo() -> list[str]:
    return por_cercania()


class _CatalogoPorFecha(list):
    """Se comporta como la lista de siempre, pero se reordena cada dia.

    Hereda de list para que todo lo que ya la usaba - len(), iterar, /catalogo
    - siga funcionando sin tocar nada."""

    def __iter__(self):
        return iter(_catalogo())

    def __len__(self):
        return len(_catalogo())

    def __getitem__(self, i):
        return _catalogo()[i]


CATALOGUE = _CatalogoPorFecha()




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
    """The article's public URL, which is also the key for "already made".

    It was nailed to es.wikipedia.org, and that is worse than it looks.
    Plenty of these titles are spelled the same in both languages - Cicada
    3301, Kryptos, Stuxnet, WikiLeaks, 4chan, Theranos - so an English case
    produced the same URL as the Spanish one already made, and the catalogue
    reported itself exhausted. The same URL is also the source link in the
    description, pointing at a Spanish article that for half of this
    catalogue does not exist."""
    return f"https://{WIKI_LANG}.wikipedia.org/wiki/" + title.replace(" ", "_")


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
