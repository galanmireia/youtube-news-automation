"""Reads a page from the open web, when it is worth reading.

research.py used to refuse this on purpose, and its docstring gave four
reasons: paywalls, PDFs, dead links, unknown licences and unknown
reliability. Three of those are real problems with real solutions, and the
fourth was a mistake:

  - Unknown reliability is solved by not fetching arbitrary pages. What gets
    fetched here is only ever a reference Wikipedia itself cites, and only
    when it sits on a domain in the list below. That is a much narrower thing
    than "the web".

  - Dead links are solved by the Wayback Machine, and for this catalogue that
    is not a nicety. A case about the internet is disproportionately a case
    about pages that no longer exist: the original posts, the site that was
    taken down, the channel that was deleted. The archive is often the only
    place the primary material survives.

  - Paywalls and PDFs are solved by discarding what comes back. A paywalled
    article returns three hundred characters of teaser, a PDF returns binary;
    both fail the length check and are dropped, at the cost of one timeout.

  - Unknown licence was the mistake. Nothing from here is ever reproduced.
    The dossier is read for FACTS - dates, figures, names, sequence - and
    facts are not copyrightable. What is copyrightable is the phrasing, and
    the phrasing is written from scratch every time. This is what any
    journalist does with a source, and the rule that keeps it true is already
    in the script prompt: never reuse a source's wording.

What is deliberately NOT in the allowlist is as important as what is: forums,
wikis, fandom pages, Medium, Blogspot, Reddit, X and YouTube. They are where
most of what is written about these cases lives, and almost all of it is
unverifiable. A channel that has to be monetisable cannot narrate a claim
whose only source is somebody who was sure.
"""
import html
import logging
import re
from urllib.parse import urlparse

import requests

from .config import CHANNEL_NAME

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": f"{CHANNEL_NAME}NewsBot/1.0 "
                  "(automated video generation; contact via YouTube channel)"
}

_TIMEOUT = 20
# A news article is thirty to eighty kilobytes of HTML. Anything past two
# megabytes is an application, not an article, and reading it is a waste of a
# timeout.
_MAX_BYTES = 2_000_000
# Under this many words, whatever came back is a cookie wall, a paywall
# teaser, a redirect notice or a 404 page that answered 200. All four look
# like success to requests and like nothing to a script.
_MIN_PALABRAS = 220

# Domains are grouped by what they are good FOR, not by prestige, because the
# groups are read in order and the first ones are what a compilation runs out
# of first.
#
# 1. The public record. Indictments, advisories, filings and rulings: the only
#    sources that carry exact figures and exact dates, which is what the data
#    slides need and what nothing else in the dossier reliably has. Most of
#    this catalogue - Silk Road, LulzSec, Theranos, OneCoin, Stuxnet,
#    WannaCry, Mirai, Snowden - has a government document behind it. Works of
#    the US federal government are also public domain, which removes the
#    licence question entirely.
_PUBLICO = (
    ".gov", ".mil", "europa.eu", "courtlistener.com", "supremecourt.gov",
    "sec.gov", "justice.gov", "fbi.gov", "cisa.gov", "nist.gov", "gao.gov",
    "treasury.gov", "ftc.gov", "europol.europa.eu", "ncsc.gov.uk",
)
# 2. Long-form. Where somebody spent three months on the case and wrote ten
#    thousand words about it. This is the group that turns a Wikipedia
#    paragraph into a story with people in it.
_LARGO = (
    "wired.com", "arstechnica.com", "newyorker.com", "theatlantic.com",
    "theverge.com", "vice.com", "propublica.org", "bellingcat.com",
    "krebsonsecurity.com", "schneier.com", "nytimes.com", "washingtonpost.com",
    "theguardian.com", "bbc.com", "bbc.co.uk", "latimes.com", "vanityfair.com",
    "wsj.com", "ft.com", "economist.com", "harpers.org", "theintercept.com",
)
# 3. General press. Rarely adds detail the first two do not have, but it is
#    what confirms a date, and a second source on a date is the difference
#    between narrating it and hedging it.
_PRENSA = (
    "reuters.com", "apnews.com", "npr.org", "cnn.com", "nbcnews.com",
    "cbsnews.com", "abcnews.go.com", "time.com", "forbes.com", "cnet.com",
    "zdnet.com", "bleepingcomputer.com", "theregister.com", "engadget.com",
    "gizmodo.com", "independent.co.uk", "telegraph.co.uk", "sky.com",
    "elpais.com", "elmundo.es", "lavanguardia.com", "spiegel.de",
    "lemonde.fr", "corriere.it", "repubblica.it", "smh.com.au",
)
# 4. Academic and archival.
_ACADEMICO = (".edu", ".ac.uk", "arxiv.org", "doi.org", "acm.org", "ieee.org",
              "nasa.gov", "archive.org", "web.archive.org")

# Read in this order, and the order is the ranking: one reference from the
# public record is worth several from the general press.
_NIVELES = (
    ("registro publico", _PUBLICO),
    ("reportaje largo", _LARGO),
    ("archivo o academico", _ACADEMICO),
    ("prensa", _PRENSA),
)

# Extensions that are not an article. PDFs are excluded rather than parsed:
# parsing them needs a dependency, and a PDF worth reading is nearly always a
# government document that also exists as a web page on the same domain.
_NO_ES_ARTICULO = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|zip|gz|mp3|mp4|avi|mov|jpe?g|png|gif|svg|webp)(\?|$)",
    re.IGNORECASE,
)

_BLOQUES_MUERTOS = re.compile(
    r"<(script|style|noscript|nav|header|footer|aside|form|figure|iframe|svg)\b.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_PARRAFO = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_ETIQUETA = re.compile(r"<[^>]+>")
_ESPACIOS = re.compile(r"\s+")

# Lines this short inside a <p> are a caption, a byline, a share button or a
# cookie notice. An actual sentence of an actual article is longer.
_MIN_LINEA = 60

_RUIDO = re.compile(
    r"(cookie|newsletter|suscr|subscri|sign up|sign in|log in|advertisement|"
    r"share this|follow us|all rights reserved|terms of (use|service)|"
    r"privacy policy|enable javascript|your browser)",
    re.IGNORECASE,
)


def nivel_de(url: str) -> tuple[int, str, str] | None:
    """Which group this URL belongs to, or None when it is not in any.

    Returns (group index, group name, the allowlist entry that matched). The
    index is for sorting - lower is better - and the entry is what the caller
    dedupes on, because the outlet is not the hostname: bbc.com and
    news.bbc.co.uk are one newsroom and reading both is reading one source
    twice.
    """
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    if not host or _NO_ES_ARTICULO.search(url):
        return None
    for indice, (nombre, dominios) in enumerate(_NIVELES):
        for dominio in dominios:
            # Suffix match so that www.bbc.co.uk and news.bbc.co.uk both match
            # bbc.co.uk, while notbbc.co.uk does not.
            if host == dominio.lstrip(".") or host.endswith(dominio if dominio.startswith(".") else "." + dominio):
                return indice, nombre, dominio
    return None


def emisor_de(url: str, dominio: str) -> str:
    """The key two URLs share when they are the same source.

    For a named outlet that is the name itself, so bbc.com and bbc.co.uk
    collapse to "bbc". For a whole-TLD entry like .gov it is the hostname,
    because justice.gov and fbi.gov are genuinely different sources and both
    are worth having.
    """
    if dominio.startswith("."):
        return (urlparse(url).hostname or url).lower().removeprefix("www.")
    return dominio.split(".")[0]


def _texto_de_html(documento: str) -> str:
    """The article out of the page.

    Deliberately crude: strip what is never prose, then keep the paragraphs.
    Every news site on the list above writes its body in <p> tags, so this
    gets the article and leaves the furniture, without a parser dependency
    whose wheel could fail to build on the deploy and cost a whole cycle.
    """
    sin_bloques = _BLOQUES_MUERTOS.sub(" ", documento)
    lineas = []
    for bruto in _PARRAFO.findall(sin_bloques):
        texto = html.unescape(_ETIQUETA.sub("", bruto))
        texto = _ESPACIOS.sub(" ", texto).strip()
        if len(texto) < _MIN_LINEA or _RUIDO.search(texto):
            continue
        lineas.append(texto)
    # The same sentence repeated is a teaser echoed in a meta tag or a related
    # articles rail, and it is common enough to be worth one set.
    vistas: set[str] = set()
    unicas = []
    for linea in lineas:
        if linea in vistas:
            continue
        vistas.add(linea)
        unicas.append(linea)
    return "\n\n".join(unicas)


def _descargar(url: str) -> str:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT,
                         allow_redirects=True, stream=True)
        if r.status_code != 200:
            return ""
        tipo = (r.headers.get("Content-Type") or "").lower()
        if "html" not in tipo:
            return ""
        trozos, total = [], 0
        for trozo in r.iter_content(chunk_size=65536, decode_unicode=False):
            trozos.append(trozo)
            total += len(trozo)
            if total > _MAX_BYTES:
                break
        r.close()
        bruto = b"".join(trozos)
        return bruto.decode(r.encoding or "utf-8", errors="replace")
    except (requests.RequestException, ValueError, UnicodeDecodeError):
        return ""


def _en_el_archivo(url: str) -> str:
    """The Wayback Machine's snapshot of this URL, when it has one."""
    try:
        r = requests.get("https://archive.org/wayback/available",
                         params={"url": url}, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        foto = (r.json().get("archived_snapshots") or {}).get("closest") or {}
    except (requests.RequestException, ValueError, AttributeError):
        return ""
    return foto.get("url", "") if foto.get("available") else ""


def leer(url: str) -> tuple[str, str]:
    """(text, url actually read). Empty text when nothing usable came back.

    The archive is tried whenever the live page fails OR comes back too
    short, not only on a hard 404: a page that has been replaced by a
    paywall, a parking notice or a redirect to a homepage answers 200 and is
    just as dead, and for these cases the archive still holds what it said.
    """
    texto = _texto_de_html(_descargar(url))
    if len(texto.split()) >= _MIN_PALABRAS:
        return texto, url

    copia = _en_el_archivo(url)
    if not copia:
        return "", ""
    archivado = _texto_de_html(_descargar(copia))
    if len(archivado.split()) >= _MIN_PALABRAS:
        logger.info("Pagina muerta o recortada, leida del archivo: %s", url)
        return archivado, copia
    return "", ""
