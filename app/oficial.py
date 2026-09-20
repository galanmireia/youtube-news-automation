"""Material oficial: lo que se puede usar porque no es de nadie.

Esto sale de una pregunta suya - "¿no hay material oficial que se pueda
difundir?" - y la respuesta en España tiene dos mitades muy distintas, asi
que conviene no mezclarlas:

LOS TEXTOS, SI. El articulo 13 de la Ley de Propiedad Intelectual deja fuera
de la propiedad intelectual "las resoluciones de los organos jurisdiccionales
y los actos, acuerdos, deliberaciones y dictamenes de los organismos
publicos". O sea que una SENTENCIA no es de nadie: se puede citar entera,
leerla en voz alta y sacarla en pantalla. Para un canal de sucesos eso es
material de primera - los hechos probados de una sentencia son la mejor
fuente que hay de un caso, y ademas es la unica que no se puede desmentir.
Se consultan en el CENDOJ, el buscador publico del Poder Judicial.

LAS FOTOS, NO. Aqui no funciona como en Estados Unidos, donde lo que hace un
organismo federal nace en dominio publico. En España una foto de la Policia o
de la Guardia Civil sigue teniendo su autor y su titular, y que se difunda
para que la publique la prensa no la convierte en libre. Asi que no hay un
"banco oficial" de caras del que tirar.

Lo que si aporta este modulo es la fuente de fotos libres que faltaba por
mirar: WIKIDATA. Es distinta de las tres de real_photos, porque Wikidata
guarda la foto de una persona (propiedad P18) aunque el articulo de Wikipedia
no la lleve dentro, y tiene ficha de gente que no tiene articulo propio.
"""
from __future__ import annotations

import logging

import requests

from .config import CHANNEL_NAME

logger = logging.getLogger(__name__)

_API = "https://www.wikidata.org/w/api.php"
_COMMONS = "https://commons.wikimedia.org/w/api.php"
_HEADERS = {"User-Agent": f"{CHANNEL_NAME}Bot/1.0 "
                          "(https://github.com/galanmireia/youtube-news-automation) python-requests"}

CENDOJ = "https://www.poderjudicial.es/search/indexAN.jsp"

# El aviso que acompaña a una sentencia, para que no se lea como un permiso
# generico: lo que es libre es el TEXTO de la resolucion, no lo que la rodea.
NOTA_SENTENCIA = (
    "Las sentencias no son de nadie (art. 13 LPI): se pueden citar, leer y "
    "sacar en pantalla. Ojo, eso vale para el texto de la resolucion, no para "
    "el reportaje de un periodico que la cuenta."
)


def _pide(url: str, params: dict) -> dict:
    try:
        r = requests.get(url, params=params, headers=_HEADERS, timeout=25)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        logger.warning("Wikidata/Commons no ha contestado a %s", params.get("search")
                       or params.get("entity") or params.get("titles"))
        return {}


def _es_persona(entidad: str) -> bool:
    """P31 = "instancia de". Q5 = ser humano.

    Es la comprobacion que a mano costo tres arreglos: sin ella "Rosario
    Porto" casa con la ciudad de Rosario y "Teo" con Teo Macero. Wikidata lo
    dice en un campo, sin tener que adivinarlo por el titulo.
    """
    datos = _pide(_API, {"action": "wbgetclaims", "entity": entidad,
                         "property": "P31", "format": "json"})
    for c in (datos.get("claims", {}) or {}).get("P31", []):
        valor = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(valor, dict) and valor.get("id") == "Q5":
            return True
    return False


def _url_en_commons(fichero: str) -> str:
    datos = _pide(_COMMONS, {"action": "query", "prop": "imageinfo", "iiprop": "url",
                             "titles": f"File:{fichero}", "format": "json"})
    for p in (datos.get("query", {}).get("pages", {}) or {}).values():
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("url"):
            return info["url"]
    return ""


def retrato(nombre: str, idioma: str = "es") -> tuple[str, str] | None:
    """La foto que Wikidata tiene fichada para esa persona, si la tiene.

    Devuelve (url, nombre de fichero). Solo mira fichas de personas: si lo que
    encuentra con ese nombre es una ciudad o un equipo de futbol, no vale.
    """
    busqueda = _pide(_API, {"action": "wbsearchentities", "search": nombre,
                            "language": idioma, "uselang": idioma,
                            "format": "json", "limit": 5, "type": "item"})
    for cand in busqueda.get("search", []):
        eid = cand.get("id")
        if not eid or not _es_persona(eid):
            continue
        claims = _pide(_API, {"action": "wbgetclaims", "entity": eid,
                              "property": "P18", "format": "json"})
        for c in (claims.get("claims", {}) or {}).get("P18", []):
            fichero = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            if not fichero:
                continue
            url = _url_en_commons(fichero)
            if url:
                logger.info("Wikidata tiene retrato de «%s» (%s): %s", nombre, eid, fichero)
                return url, fichero
        logger.info("Wikidata ficha a «%s» (%s) pero sin foto.", nombre, eid)
    return None


def buscar_sentencia(caso: str) -> str:
    """El enlace al buscador publico de sentencias. No raspa nada: da la puerta.

    El CENDOJ va por formulario y sesion, asi que no tiene sentido fingir que
    se puede consultar desde aqui; lo util es llevarla al sitio correcto y
    decirle lo que puede hacer con lo que encuentre.
    """
    return CENDOJ
