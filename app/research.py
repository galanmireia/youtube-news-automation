"""Builds a dossier on one case instead of reading a single article.

A seventeen-minute narration is around four thousand words OF SUBSTANCE. The
Spanish Wikipedia article on a disaster, truncated at nine thousand
characters, is about fifteen hundred - most of it repeated in the lead. Asking
for a longer video over that source does not produce a longer story, it
produces the same story with filler, which is exactly the failure this is
here to prevent.

Three things widen the source material, in descending order of how much they
give back per line of code here:

  1. Stop truncating. Nine thousand characters was sized for a sixty-second
     Short. The main article is now read at length.

  2. Read it in several languages. Wikipedia articles are not translations of
     each other - they are written separately, and a disaster's most detailed
     article is usually the one in the language of the country it happened in,
     with English close behind. The English article on the Costa Concordia is
     several times the Spanish one and carries the technical detail; the
     Italian one carries the trial. Which languages exist is asked, not
     assumed, via langlinks.

  3. Read what the case is made of. A disaster is never one article: there is
     one for the ship, one for the captain, one for the island, one for the
     operator, one for the regulation that changed afterwards. Those are the
     specifics a script runs out of first. They are found by taking the
     article's own outgoing links and keeping the ones the article itself
     keeps coming back to.

What this module deliberately does not do is follow citations out to the open
web. Wikipedia's references are where the real reports live, but they are
arbitrary third-party pages - paywalls, PDFs, dead links, unknown licences,
unknown reliability - and fetching them at generation time would be slow,
fragile and legally murky. Everything here stays inside Wikimedia, which is
free-licensed, fast, and consistent in shape.
"""
import logging
import re
import unicodedata

import requests

from .config import CHANNEL_NAME

logger = logging.getLogger(__name__)

# The main article, read at length rather than trimmed to a Short's appetite.
# Claude's input is cheap next to its output - forty thousand characters is
# about eleven thousand tokens, roughly two cents - and the story sits after
# the prompt-cache marker, so a bigger dossier does not invalidate the cached
# instructions.
_MAIN_CHARS = 40000
_OTHER_LANG_CHARS = 25000
_RELATED_CHARS = 7000

# Spanish first because it is the channel's language and the names and
# spellings should come from it. English second: three times the size and
# where the engineering detail usually is. The rest are the languages the
# cases in the catalogue actually happened in.
_LANG_PRIORITY = ("es", "en", "it", "fr", "de", "pt", "nl", "ru", "ja", "no", "sv")
_MAX_LANGS = 3
_MAX_RELATED = 7

_HEADERS = {
    "User-Agent": f"{CHANNEL_NAME}NewsBot/1.0 "
                  "(automated video generation; contact via YouTube channel)"
}

# Links that are never the subject of anything. A country, a century or a unit
# of measurement is linked by every article and tells a script nothing, so they
# are dropped before the relevance scoring rather than being allowed to win it
# on sheer frequency.
_GENERIC_LINK = re.compile(
    r"^(\d{1,4}|siglo\s|anexo:|categor|wikiproyecto|portal:|plantilla:|"
    r"lista de|idioma |lengua |metro|kilómetro|tonelada|milla|nudo \(|"
    r"océano|mar |continente|europa$|asia$|áfrica$|américa|oceanía$)",
    re.IGNORECASE,
)


def _api(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def _get(lang: str, **params) -> dict:
    params.setdefault("format", "json")
    params.setdefault("redirects", 1)
    try:
        r = requests.get(_api(lang), params=params, headers=_HEADERS, timeout=25)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        return {}


def _extract(lang: str, title: str, limit: int) -> str:
    """One article's plain text. Empty when the page has none."""
    data = _get(lang, action="query", prop="extracts", explaintext=1,
                exsectionformat="plain", titles=title)
    for page in data.get("query", {}).get("pages", {}).values():
        texto = (page.get("extract") or "").strip()
        if texto:
            return texto[:limit]
    return ""


def _translations(lang: str, title: str) -> dict[str, str]:
    """The same article's title in every other language that has it."""
    data = _get(lang, action="query", prop="langlinks", lllimit=500, titles=title)
    out = {}
    for page in data.get("query", {}).get("pages", {}).values():
        for link in page.get("langlinks") or []:
            if link.get("lang") and link.get("*"):
                out[link["lang"]] = link["*"]
    return out


def _fold(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c))


def _related_titles(lang: str, title: str, cuerpo: str) -> list[str]:
    """The articles this case is actually made of.

    Every article links to hundreds of others; almost all of them are
    incidental. The ones worth reading are the ones the text itself returns
    to, so each link is scored by how often its title appears in the body.
    Mentioned once is a passing reference; mentioned repeatedly is a subject.
    """
    data = _get(lang, action="query", prop="links", plnamespace=0, pllimit=500, titles=title)
    enlaces: list[str] = []
    for page in data.get("query", {}).get("pages", {}).values():
        enlaces += [l["title"] for l in (page.get("links") or []) if l.get("title")]

    cuerpo_plegado = _fold(cuerpo)
    puntuados = []
    for enlace in enlaces:
        if _GENERIC_LINK.match(enlace) or len(enlace) < 4:
            continue
        # The parenthesised qualifier is not part of how the article writes the
        # name: "Giglio (isla)" appears in the text simply as "Giglio".
        desnudo = re.sub(r"\s*\([^)]*\)\s*$", "", enlace)
        # An article names somebody in full once and by surname for the rest of
        # the page, so counting only the full title undercounts exactly the
        # subject that matters most. Measured on the Costa Concordia article,
        # "Francesco Schettino" appears once and "Schettino" four times, which
        # was enough to drop the protagonist out of the dossier entirely. The
        # distinctive last word is counted too, and the better count wins.
        ultimo = desnudo.rsplit(" ", 1)[-1]
        veces = cuerpo_plegado.count(_fold(desnudo))
        if len(ultimo) >= 5:
            veces = max(veces, cuerpo_plegado.count(_fold(ultimo)))
        if veces >= 2:
            puntuados.append((veces, len(desnudo), enlace))
    # Most mentioned first; on a tie the longer name, which is the more
    # specific subject ("Francesco Schettino" over "Schettino").
    puntuados.sort(key=lambda x: (-x[0], -x[1]))
    return [enlace for _, _, enlace in puntuados[:_MAX_RELATED]]


_IDIOMA = {
    "es": "español", "en": "inglés", "it": "italiano", "fr": "francés",
    "de": "alemán", "pt": "portugués", "nl": "neerlandés", "ru": "ruso",
    "ja": "japonés", "no": "noruego", "sv": "sueco",
}


def build_dossier(title: str, lang: str = "es") -> str:
    """Everything Wikimedia has on this case, labelled by where it came from.

    Labelled on purpose: the script is told to cross its sources, and it can
    only do that if it can tell them apart. An unlabelled wall of text reads
    as one document that contradicts itself."""
    partes: list[str] = []

    principal = _extract(lang, title, _MAIN_CHARS)
    if not principal:
        logger.warning("El articulo %r en %s no tiene texto; no hay dosier.", title, lang)
        return ""
    partes.append(
        f"===== FUENTE 1 · Wikipedia en {_IDIOMA.get(lang, lang)} · «{title}» =====\n{principal}"
    )

    otros = _translations(lang, title)
    elegidos = [(l, otros[l]) for l in _LANG_PRIORITY if l in otros and l != lang][: _MAX_LANGS - 1]
    for otro_lang, otro_titulo in elegidos:
        texto = _extract(otro_lang, otro_titulo, _OTHER_LANG_CHARS)
        if not texto:
            continue
        partes.append(
            f"===== FUENTE {len(partes) + 1} · Wikipedia en "
            f"{_IDIOMA.get(otro_lang, otro_lang)} · «{otro_titulo}» =====\n"
            f"(Articulo escrito de forma independiente del anterior, no es su traduccion: "
            f"puede traer datos que el otro no tiene.)\n{texto}"
        )

    for relacionado in _related_titles(lang, title, principal):
        texto = _extract(lang, relacionado, _RELATED_CHARS)
        if not texto:
            continue
        partes.append(
            f"===== FUENTE {len(partes) + 1} · articulo relacionado · «{relacionado}» =====\n{texto}"
        )

    dosier = "\n\n".join(partes)
    logger.info(
        "Dosier de %r: %s fuentes, %s caracteres (idiomas: %s; relacionados: %s).",
        title, len(partes), len(dosier),
        ", ".join([lang] + [l for l, _ in elegidos]),
        len(partes) - 1 - len(elegidos),
    )
    return dosier
