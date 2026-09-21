"""Metraje real y libre de Archive.org.

De aqui sale la unica cosa que de verdad nos faltaba de OpenMontage: ellos
buscan VIDEO REAL EN MOVIMIENTO en archivos abiertos, y nosotros no miramos
Archive.org para nada. Para el calendario del canal eso importa mucho, porque
casi todo lo que hay en el son efemerides de hechos historicos - el naufragio
del Estonia en 1994, el Costa Concordia en 2012 - y de eso si existe metraje
libre. Una foto fija de un barco no cuenta lo mismo que el barco escorado.

DOS TRAMPAS, y las dos son de las que ya nos han mordido:

La primera es la de la Wikipedia inglesa otra vez. Archive.org es un ARCHIVO,
no un banco de material libre: aloja muchisimo que no se puede reutilizar,
porque su trabajo es conservarlo, no darte permiso. Que algo se pueda ver y
descargar no dice nada de si se puede publicar. Asi que aqui no vale el
criterio de "esta en Archive.org": hace falta licencia explicita, o una
coleccion que sea dominio publico entera.

La segunda es mas fina y es especifica de este canal: las licencias NC -no
comercial- NO SIRVEN. Un canal monetizado es uso comercial, y eso convierte
una licencia que parece libre en una infraccion con el agravante de que
estaba escrito. Lo mismo con ND, que prohibe obras derivadas: montar un clip
dentro de un video es derivar. Se descartan las dos.
"""
from __future__ import annotations

import logging

import requests

from .config import CHANNEL_NAME

logger = logging.getLogger(__name__)

_BUSCAR = "https://archive.org/advancedsearch.php"
_METADATOS = "https://archive.org/metadata/"
_DESCARGA = "https://archive.org/download/"
_HEADERS = {"User-Agent": f"{CHANNEL_NAME}Bot/1.0 "
                          "(https://github.com/galanmireia/youtube-news-automation) python-requests"}

# Licencias que si permiten publicar en un canal monetizado.
_LICENCIAS_OK = (
    "creativecommons.org/publicdomain/zero",
    "creativecommons.org/publicdomain/mark",
    "creativecommons.org/licenses/by/",
    "creativecommons.org/licenses/by-sa/",
)
# Y las que NO, aunque lleven "creativecommons" en la url y lo parezcan.
_LICENCIAS_NO = ("by-nc", "by-nd", "nc-sa", "nc-nd", "noncommercial")

# Colecciones que son dominio publico enteras, para el material sin campo de
# licencia. Lista corta a proposito: cada una tiene que poder defenderse.
_COLECCIONES_LIBRES = frozenset({
    "prelinger",        # Archivo Prelinger, dominio publico declarado
    "nasa",             # obra del gobierno de EEUU
    "usgovfilms",       # idem
    "publicmovies",     # cine en dominio publico
})

# Formatos utiles: comprimidos y reproducibles. El original suele ser un
# MPEG2 de varios gigas que no hace falta para un plano de cuatro segundos.
_FORMATOS = ("h.264", "512kb mpeg4", "mpeg4", "ogg video", "h.264 ia")


def _pide(url: str, params: dict | None = None) -> dict:
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        logger.warning("Archive.org no ha contestado a %s", url)
        return {}


def _licencia_vale(licenseurl: str, colecciones) -> tuple[bool, str]:
    """(se puede usar, por que). El porque se enseña: es lo que deja auditarlo."""
    url = (licenseurl or "").lower()
    if any(malo in url for malo in _LICENCIAS_NO):
        return False, "licencia no comercial o sin derivados"
    if any(buena in url for buena in _LICENCIAS_OK):
        return True, licenseurl
    if isinstance(colecciones, str):
        colecciones = [colecciones]
    libres = _COLECCIONES_LIBRES & {str(c).lower() for c in (colecciones or [])}
    if libres:
        return True, f"coleccion de dominio publico ({sorted(libres)[0]})"
    return False, "sin licencia declarada"


def buscar(consulta: str, cuantos: int = 8) -> list[dict]:
    """Peliculas libres de Archive.org que hablen de esto.

    Devuelve solo lo que se puede publicar, con el motivo al lado.
    """
    datos = _pide(_BUSCAR, {
        "q": f'{consulta} AND mediatype:(movies)',
        "fl[]": ["identifier", "title", "year", "licenseurl", "collection", "downloads"],
        "rows": 50, "page": 1, "output": "json",
        "sort[]": "downloads desc",
    })
    docs = (datos.get("response") or {}).get("docs") or []
    salida, descartados = [], 0
    for d in docs:
        vale, motivo = _licencia_vale(d.get("licenseurl", ""), d.get("collection"))
        if not vale:
            descartados += 1
            continue
        salida.append({
            "id": d.get("identifier", ""),
            "titulo": d.get("title", ""),
            "año": d.get("year", ""),
            "licencia": motivo,
            "descargas": d.get("downloads", 0),
        })
        if len(salida) >= cuantos:
            break
    logger.info("Archive.org «%s»: %s utilizables de %s (descartados %s por licencia).",
                consulta, len(salida), len(docs), descartados)
    return salida


def clips_de(identificador: str) -> list[dict]:
    """Los ficheros de video reproducibles de una pieza, del mas ligero arriba."""
    datos = _pide(_METADATOS + identificador)
    ficheros = []
    for f in datos.get("files") or []:
        formato = (f.get("format") or "").lower()
        if formato not in _FORMATOS:
            continue
        try:
            tamaño = int(f.get("size") or 0)
        except (TypeError, ValueError):
            tamaño = 0
        ficheros.append({
            "nombre": f.get("name", ""),
            "formato": f.get("format", ""),
            "bytes": tamaño,
            "segundos": f.get("length", ""),
            "url": f"{_DESCARGA}{identificador}/{requests.utils.quote(f.get('name', ''))}",
        })
    ficheros.sort(key=lambda f: f["bytes"] or 1 << 62)
    return ficheros


def credito_de(item: dict) -> str:
    """La atribucion, que en CC-BY no es cortesia sino condicion de la licencia."""
    trozos = [t for t in (item.get("titulo"), str(item.get("año") or "")) if t]
    return f"{' '.join(trozos)} — Internet Archive ({item.get('licencia', '')})"
