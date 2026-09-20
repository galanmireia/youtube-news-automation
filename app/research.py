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

  4. Read the sources Wikipedia read. This module used to refuse to, and the
     refusal is now wrong for this catalogue. A Wikipedia article is a
     summary written to be short: it gives the sequence of a case and almost
     none of the texture, and every channel covering these cases is reading
     that same summary. The references under it are where somebody actually
     went and looked - the indictment with the figures in it, the ten
     thousand word reportage with the people in it, the archived copy of the
     page that no longer exists. What made this risky was fetching arbitrary
     pages; open_web.py does not do that. It reads only a reference the
     article itself cites, only from a list of domains, and only for facts,
     which is what a journalist does with a source and is not a licence
     question. See that module for the rest of the reasoning.
"""
import concurrent.futures
import logging
import re
import unicodedata

import requests

from . import open_web
from .config import CHANNEL_NAME, WIKI_LANG

logger = logging.getLogger(__name__)

# The main article, read at length rather than trimmed to a Short's appetite.
# Claude's input is cheap next to its output - forty thousand characters is
# about eleven thousand tokens, roughly two cents - and the story sits after
# the prompt-cache marker, so a bigger dossier does not invalidate the cached
# instructions.
_MAIN_CHARS = 40000
_OTHER_LANG_CHARS = 25000
_RELATED_CHARS = 7000

# The channel's language first, because the names and spellings should come
# from the article the script is actually written off. The rest are the
# languages these cases happened in, and they are read for what the main
# article does not have: the trial, the local consequences, the detail the
# English write-up skipped.
_LANG_PRIORITY = (WIKI_LANG,) + tuple(
    l for l in ("en", "es", "it", "fr", "de", "pt", "nl", "ru", "ja", "no", "sv")
    if l != WIKI_LANG
)
_MAX_LANGS = 3
_MAX_RELATED = 7

# References are the slowest part of the dossier by far - a dead domain costs
# a full timeout - and in compilation mode this runs once per case, so the
# budget is small and the reads happen at the same time rather than one after
# another. Four good references is already more first-hand material than the
# Wikipedia article itself carries.
_MAX_REFERENCIAS = 6
_REF_CHARS = 14000
# Attempts are made at the same time, so trying eighteen costs the same wall
# clock as trying eight: about two rounds of one timeout. Measured on Silk
# Road, half of what is attempted comes back dead or paywalled, so the
# attempts have to outnumber the places by a good margin or the budget is
# spent on failures.
_INTENTOS_POR_PLAZA = 3
# One per domain. Six BBC pages about the same case are one source that has
# been fetched six times, and they crowd out the indictment.
_MAX_POR_DOMINIO = 1

_HEADERS = {
    "User-Agent": f"{CHANNEL_NAME}NewsBot/1.0 "
                  "(automated video generation; contact via YouTube channel)"
}

# Links that are never the subject of anything. A country, a century or a unit
# of measurement is linked by every article and tells a script nothing, so they
# are dropped before the relevance scoring rather than being allowed to win it
# on sheer frequency.
_GENERIC_LINK = re.compile(
    r"^(\d{1,4}|siglo\s|century$|anexo:|categor|wikiproyecto|portal:|plantilla:|"
    r"template:|list of |lista de|idioma |lengua |language$|metro|kilómetro|"
    r"kilometer|tonelada|milla|mile$|nudo \(|knot \(|"
    r"océano|ocean$|mar |sea$|continente|continent$|europa$|europe$|asia$|"
    r"áfrica$|africa$|américa|america$|oceanía$|oceania$|"
    # The computing equivalents, in both languages. Measured on the Morris worm
    # dossier, where frequency scoring returned "Unix", "Correo electrónico",
    # "Universidad de Berkeley" and "Gusano informático" - four generic
    # articles, 4,166 words, more than half the dossier, none of them about the
    # case. They score highly for the same reason they are useless: the article
    # says "Unix" and "email" constantly, because that is what the worm
    # travelled through.
    #
    # The English half is not a translation for tidiness. This list is the only
    # thing standing between the dossier and that failure, and a Spanish-only
    # pattern matches nothing at all in an English article - the bug would have
    # come back whole, silently, the first time a video was generated.
    r"unix$|linux$|internet$|correo electr|email$|e-mail$|ordenador|computadora|"
    r"computer$|software$|hardware$|programa \(|lenguaje de programaci|"
    r"programming language$|sistema operativo$|operating system$|"
    r"universidad de |university of |instituto de |institute of |"
    r"red de computadoras$|computer network$|servidor$|server$|"
    r"protocolo$|protocol$|algoritmo$|algorithm$|criptograf|cryptograph|"
    r"encryption$|contrase|password$|informática$|computing$|computer science$|"
    r"programador$|programmer$|world wide web$|website$|web browser$)",
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


def _menciona(cuerpo: str, caso: str) -> bool:
    """Does this article talk about the case, or merely get mentioned by it?

    Frequency scoring cannot tell those apart, and they are opposites. The
    Morris worm article says "correo" constantly, because that is what the
    worm travelled through - but Wikipedia's article on email does not mention
    Morris at all. It is background, and background sent to a script prompt
    comes back as a paragraph explaining what email is.

    Reciprocity separates them, and costs nothing: the text has already been
    fetched. An article that names the case back is writing about it. One that
    never does is a definition the reader did not ask for."""
    desnudo = re.sub(r"\s*\([^)]*\)\s*$", "", caso)
    plegado = _fold(cuerpo)
    if _fold(desnudo) in plegado:
        return True
    # Same rule as the scoring: an article names somebody in full once and by
    # surname after that, so the distinctive last word counts as the name.
    ultimo = desnudo.rsplit(" ", 1)[-1]
    return len(ultimo) >= 5 and _fold(ultimo) in plegado


def existe(lang: str, title: str) -> bool:
    """Is there an article under this exact name?

    Worth its own call because the two ways a probe comes back empty look
    identical from the outside and mean opposite things. "The article exists
    and cites nothing we can read" is a finding about the case. "There is no
    such article" is a typo. Reporting the second as the first is how you
    conclude a feature does not work without ever having tested it."""
    data = _get(lang, action="query", titles=title)
    paginas = data.get("query", {}).get("pages", {})
    return any("missing" not in p for p in paginas.values()) if paginas else False


def existen(lang: str, titulos: list[str], lote: int = 50) -> dict[str, bool]:
    """Which of these articles exist, asked fifty at a time.

    The API takes many titles per request, so checking a whole catalogue is
    two calls rather than fifty-eight. A title that is missing is reported as
    missing; a batch whose request FAILED is left out of the result entirely
    rather than reported as missing, because a network blip that answers
    "your catalogue is broken" is worse than no answer."""
    resultado: dict[str, bool] = {}
    for i in range(0, len(titulos), lote):
        grupo = titulos[i:i + lote]
        consulta = _get(lang, action="query", titles="|".join(grupo)).get("query", {})
        paginas = consulta.get("pages")
        if not paginas:
            continue
        # A title can be normalised ("cicada 3301" -> "Cicada 3301") and then
        # redirected, so what comes back is keyed by the FINAL name and has to
        # be followed back to the one that was asked for.
        salto: dict[str, str] = {}
        for paso in ("normalized", "redirects"):
            for m in consulta.get(paso) or []:
                if m.get("from") and m.get("to"):
                    salto[m["from"]] = m["to"]

        def final(t: str) -> str:
            visto: set[str] = set()
            while t in salto and t not in visto:
                visto.add(t)
                t = salto[t]
            return t

        faltan = {p.get("title") for p in paginas.values() if "missing" in p}
        for t in grupo:
            resultado[t] = final(t) not in faltan
    return resultado


def buscar(lang: str, texto: str, cuantos: int = 3) -> list[str]:
    """What Wikipedia would find for this name. Used to propose a fix, never
    to apply one: a search that quietly picks the first hit is how "Silk Road"
    becomes a video about a trade route."""
    data = _get(lang, action="query", list="search", srsearch=texto, srlimit=cuantos)
    return [r.get("title", "") for r in data.get("query", {}).get("search", []) if r.get("title")]


def _enlaces_externos(lang: str, title: str) -> list[str]:
    """Every external URL the article cites."""
    data = _get(lang, action="query", prop="extlinks", ellimit=500, titles=title)
    urls = []
    for page in data.get("query", {}).get("pages", {}).values():
        for enlace in page.get("extlinks") or []:
            url = enlace.get("*") or ""
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http"):
                urls.append(url)
    return urls


def referencias_de(articulos: list[tuple[str, str]]) -> list[tuple[int, str, str]]:
    """The references worth reading, best first, as (rank, group name, url).

    Pooled across every language article being read, because which sources an
    article cites depends on who wrote it: the Spanish article cites Spanish
    press, the English one cites the reporting that the Spanish one is
    summarising. Ranking is by group, so one court document outranks any
    amount of general press, and no domain appears twice.
    """
    candidatas: list[tuple[int, str, str, str]] = []
    vistas: set[str] = set()
    for lang, titulo in articulos:
        for url in _enlaces_externos(lang, titulo):
            limpia = url.split("#")[0]
            if limpia in vistas:
                continue
            vistas.add(limpia)
            nivel = open_web.nivel_de(limpia)
            if nivel:
                rango, nombre, dominio = nivel
                candidatas.append((rango, nombre, limpia, dominio))

    candidatas.sort(key=lambda c: c[0])
    por_emisor: dict[str, int] = {}
    elegidas: list[tuple[int, str, str]] = []
    for rango, nombre, url, dominio in candidatas:
        emisor = open_web.emisor_de(url, dominio)
        if por_emisor.get(emisor, 0) >= _MAX_POR_DOMINIO:
            continue
        por_emisor[emisor] = por_emisor.get(emisor, 0) + 1
        elegidas.append((rango, nombre, url))

    # Best-first was wrong, and the first real case showed it: Silk Road cites
    # a lot of .gov, so six of the eight attempts went to government pages -
    # several of them two-hundred-word press releases - and the long-form
    # reportage, which is where the story actually is, got one slot.
    #
    # So the groups take turns: the best public document, then the best
    # reportage, then the best archive, then the best press, then the second
    # of each. The ranking still decides who goes first inside a group and who
    # opens the list; it no longer decides everything.
    por_nivel: dict[int, list] = {}
    for candidata in elegidas:
        por_nivel.setdefault(candidata[0], []).append(candidata)
    mezcladas = []
    for i in range(max((len(v) for v in por_nivel.values()), default=0)):
        for rango in sorted(por_nivel):
            if i < len(por_nivel[rango]):
                mezcladas.append(por_nivel[rango][i])
    return mezcladas


def leer_referencias(candidatas: list[tuple[int, str, str]],
                     cuantas: int = _MAX_REFERENCIAS) -> list[tuple[str, str, str, str]]:
    """Read the top candidates at the same time.

    Returns (group, url asked for, url actually read, text). The two URLs are
    both reported because they differ exactly when it matters: a page rescued
    from the archive comes back under a web.archive.org address, and a caller
    that only had that one could not tell which reference it belonged to - it
    would look like a reference that failed plus one that appeared from
    nowhere.

    More candidates are attempted than are wanted, because a good share of
    them come back empty - paywalled, parked, or gone without an archived
    copy - and finding that out costs a timeout either way. Reading them in
    parallel means the whole set costs one timeout rather than eight.
    """
    intentos = candidatas[: cuantas * _INTENTOS_POR_PLAZA]
    if not intentos:
        return []
    leidas: list[tuple[str, str, str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futuros = {pool.submit(open_web.leer, url): (nombre, url)
                   for _, nombre, url in intentos}
        resultados = {}
        for futuro in concurrent.futures.as_completed(futuros):
            nombre, url = futuros[futuro]
            try:
                texto, url_real = futuro.result()
            except Exception:  # noqa: BLE001 - one bad page never stops a dossier
                logger.warning("Fallo leyendo la referencia %s", url, exc_info=True)
                continue
            if texto:
                resultados[url] = (nombre, url, url_real, texto)
    # Back into ranked order: as_completed returns them by who answered first,
    # which is the opposite of the order that matters.
    for _, _, url in intentos:
        if url in resultados and len(leidas) < cuantas:
            leidas.append(resultados[url])
    return leidas


_IDIOMA = {
    "es": "español", "en": "inglés", "it": "italiano", "fr": "francés",
    "de": "alemán", "pt": "portugués", "nl": "neerlandés", "ru": "ruso",
    "ja": "japonés", "no": "noruego", "sv": "sueco",
}


def build_dossier(title: str, lang: str = WIKI_LANG) -> str:
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

    descartados = []
    for relacionado in _related_titles(lang, title, principal):
        texto = _extract(lang, relacionado, _RELATED_CHARS)
        if not texto:
            continue
        if not _menciona(texto, title):
            descartados.append(relacionado)
            continue
        partes.append(
            f"===== FUENTE {len(partes) + 1} · articulo relacionado · «{relacionado}» =====\n{texto}"
        )

    articulos = [(lang, title)] + elegidos
    candidatas = referencias_de(articulos)
    referencias = leer_referencias(candidatas)
    for nombre, _pedida, url, texto in referencias:
        partes.append(
            f"===== FUENTE {len(partes) + 1} · {nombre} · {url} =====\n"
            f"(Fuente citada por Wikipedia, leida directamente. Es material de "
            f"primera mano: usalo para el detalle, las cifras y las fechas. "
            f"NO reproduzcas su redaccion.)\n{texto[:_REF_CHARS]}"
        )

    dosier = "\n\n".join(partes)
    logger.info(
        "Dosier de %r: %s fuentes, %s caracteres (idiomas: %s; relacionados: %s; "
        "referencias: %s de %s candidatas).",
        title, len(partes), len(dosier),
        ", ".join([lang] + [l for l, _ in elegidos]),
        len(partes) - 1 - len(elegidos) - len(referencias),
        len(referencias), len(candidatas),
    )
    if referencias:
        logger.info("Referencias leidas: %s.",
                    "; ".join(f"{n} · {u}" for n, _p, u, _t in referencias))
    if descartados:
        logger.info(
            "Descartados por no mencionar %r (son contexto, no fuente): %s.",
            title, ", ".join(descartados),
        )
    return dosier
