"""De que hablamos hoy: historia de España.

Sustituye al calendario de efemerides de sucesos, que era el nicho anterior.
Y no es una lista de titulos escrita de memoria - eso ya salio mal dos veces,
con articulos inventados que no existian en Wikipedia - sino las CATEGORIAS de
la Wikipedia en español, que se recorren y devuelven articulos que existen
seguro porque vienen de ella.

La otra razon para tirar de Wikipedia: para un Short hace falta UN hecho, no
un dosier. Y el primer parrafo de un articulo historico casi siempre trae el
hecho entero.
"""
from __future__ import annotations

import logging
import random
import re
from datetime import datetime, timedelta, timezone

import requests

from . import research
from .config import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)

# De lo concreto a lo general. Un Short necesita algo que pase, con gente
# dentro: "Batallas de España" da material; "Historia de España" da ensayos.
# Historia DE ESPAÑA, y que pase EN España.
#
# Aqui tenia "Conquista de América", "Conquistadores españoles" y
# "Exploradores de España", y el video #80 salio sobre el reparto de indigenas
# en encomienda. Es historia de España en el sentido academico, pero el canal
# se llama España Contada y dice "nuestra historia": quien lo abre espera algo
# que suene a aqui. Fuera.
#
# Cada categoria de esta lista tiene que cumplir dos cosas: que sus articulos
# sean HECHOS (no institutos ni edificios) y que pasen en la peninsula, las
# islas o Ceuta y Melilla.
CATEGORIAS = (
    "Categoría:Batallas de la guerra civil española",
    "Categoría:Guerra civil española",
    "Categoría:Batallas de la guerra de la Independencia Española",
    "Categoría:Reconquista",
    "Categoría:Al-Ándalus",
    "Categoría:Motines y revueltas en España",
    "Categoría:Atentados en España",
    "Categoría:Naufragios de España",
    "Categoría:Accidentes ferroviarios en España",
    "Categoría:Incendios en España",
    "Categoría:Inundaciones en España",
    "Categoría:Epidemias en España",
    "Categoría:Inquisición española",
    "Categoría:Reyes de España",
    "Categoría:Monarcas de Castilla",
    "Categoría:Guerras carlistas",
)

# Lo que NO es un hecho contable en cuarenta segundos.
_NO_SIRVE = (
    # Lo que no es un articulo de contenido.
    "anexo:", "categoría:", "plantilla:", "wikiproyecto:", "portal:",
    "lista de", "cronología", "bibliografía", "historiografía",
    # Y lo que SI es un articulo pero NO es una historia. Esto salio del video
    # #78: "Centro Geográfico del Ejército", que es un organismo. Un Short
    # necesita algo que PASE, con gente dentro y un desenlace. Un instituto no
    # pasa: existe. Y no hay gancho posible para algo que solo existe.
    "centro ", "instituto", "museo", "academia", "regimiento", "batallón",
    "cuartel", "archivo ", "biblioteca", "fundación", "asociación",
    "real academia", "ministerio", "dirección general", "escuela ",
    "universidad", "hospital ", "parque ", "estadio", "aeropuerto",
    "carretera", "estación de", "línea ", "revista ", "periódico",
    "premio ", "orden de", "condecoración", "escudo de", "bandera de",
    "himno", "moneda de", "iglesia de", "catedral de", "castillo de",
    "palacio de", "monasterio", "puente de", "torre de", "plaza de",
)
_MINIMO_TITULO = 8



# ---------------------------------------------------------------------------
# DE DONDE SALE UN TEMA: de lo que ya funciona, no de mi lista.
#
# Hicimos el estudio de nichos - 38 canales de historia creciendo - y luego yo
# elegi los temas de una lista de categorias de Wikipedia escrita por mi. O sea
# que el estudio no sirvio para nada y los videos salieron sobre lo que a mi me
# parecia: un organismo militar, el reparto de indigenas en encomienda.
#
# Esto lo da la vuelta. Se mira que videos de historia en español tienen
# visitas AHORA, se sacan sus titulos, y de ahi salen los temas. Lo que decide
# ya no es mi criterio: es lo que la gente esta viendo esta semana.
#
# Las categorias de Wikipedia se quedan SOLO como respaldo, para cuando no hay
# cuota de YouTube o la busqueda no devuelve nada.
_BUSCAR = "https://www.googleapis.com/youtube/v3/search"
_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"

# Como se busca "un video de historia que funcione". Varias consultas porque
# una sola devuelve siempre el mismo puñado de canales.
_COMO_BUSCAR = (
    "historia de españa",
    "curiosidades historia españa",
    "que paso en españa",
)
_DIAS = 90


def _titulos_que_funcionan(cuantos: int = 40) -> list[tuple[str, int]]:
    """(titulo, visitas) de los videos de historia que mas se ven ahora."""
    if not YOUTUBE_API_KEY:
        return []
    desde = (datetime.now(timezone.utc) - timedelta(days=_DIAS)).isoformat().replace("+00:00", "Z")
    ids: dict[str, str] = {}
    for consulta in _COMO_BUSCAR:
        try:
            r = requests.get(_BUSCAR, params={
                "part": "snippet", "q": consulta, "type": "video", "order": "viewCount",
                "publishedAfter": desde, "regionCode": "ES", "relevanceLanguage": "es",
                "maxResults": 50, "key": YOUTUBE_API_KEY}, timeout=30)
            if r.status_code == 403:
                logger.warning("Sin cuota de YouTube para buscar temas; tiro de categorias.")
                return []
            r.raise_for_status()
        except requests.RequestException:
            logger.warning("YouTube no ha contestado buscando temas.")
            return []
        for item in r.json().get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            if vid:
                ids[vid] = item["snippet"].get("title", "")

    salida: list[tuple[str, int]] = []
    claves = list(ids)
    for i in range(0, len(claves), 50):
        try:
            r = requests.get(_VIDEOS, params={
                "part": "statistics", "id": ",".join(claves[i:i + 50]),
                "key": YOUTUBE_API_KEY}, timeout=30)
            r.raise_for_status()
        except requests.RequestException:
            continue
        for item in r.json().get("items", []):
            try:
                vistas = int(item.get("statistics", {}).get("viewCount", 0))
            except (TypeError, ValueError):
                continue
            titulo = ids.get(item.get("id"), "")
            if titulo and vistas:
                salida.append((titulo, vistas))
    salida.sort(key=lambda par: -par[1])
    logger.info("Temas: %s videos de historia mirados, el mas visto %s visitas.",
                len(salida), salida[0][1] if salida else 0)
    return salida[:cuantos]


# Lo que sobra de un titulo de YouTube y no es el tema.
_RUIDO = re.compile(
    r"\b(shorts?|historia|curiosidades|documental|resumen|explicado|en\s+\d+\s*minutos?"
    r"|lo\s+que\s+no\s+te\s+contaron|top\s*\d*|parte\s*\d+|#\w+)\b",
    re.IGNORECASE,
)


def _tema_de(titulo: str) -> str:
    """El asunto de un titulo de YouTube, sin la paja del formato.

    No hace falta que quede perfecto: lo que salga de aqui va a la busqueda de
    Wikipedia, que es tolerante. "sobre el Motin de Esquilache" encuentra el
    articulo igual. Lo que si hace falta es tirar lo que no es un tema, porque
    "de la de España" encontraria cualquier cosa.
    """
    limpio = _RUIDO.sub(" ", titulo)
    limpio = re.sub(r"[|¿?¡!:\-–—\"\u201c\u201d#]+", " ", limpio)
    # Conectores sueltos al principio, que es lo que queda al quitar la paja.
    limpio = re.sub(r"^\s*(sobre|de|del|la|el|los|las|que|lo|en|un|una)\b\s*", " ",
                    limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\s+", " ", limpio).strip(" .,")
    # Un tema necesita al menos dos palabras con contenido. Sin esto se colaba
    # "de la de España", que busca cualquier cosa y trae cualquier cosa.
    con_contenido = [p for p in limpio.split()
                     if len(p) > 3 and p.lower() not in
                     ("sobre", "para", "como", "este", "esta", "españa", "años", "año")]
    if len(con_contenido) < 2:
        return ""
    return limpio



def _vale(titulo: str) -> bool:
    bajo = titulo.lower()
    if len(titulo) < _MINIMO_TITULO:
        return False
    return not any(malo in bajo for malo in _NO_SIRVE)


def articulos_de(categoria: str, cuantos: int = 200) -> list[str]:
    # peticion() devuelve la RESPUESTA, no el JSON - lo di por hecho y por eso
    # /temas reventó con "'Response' object has no attribute 'get'". Devuelve
    # la respuesta a proposito: asi quien llama puede mirar el codigo de estado.
    respuesta = research.peticion(
        "https://es.wikipedia.org/w/api.php",
        {"action": "query", "list": "categorymembers", "cmtitle": categoria,
         "cmlimit": min(500, cuantos), "cmnamespace": 0, "format": "json"},
    )
    if respuesta is None or respuesta.status_code != 200:
        logger.warning("Wikipedia no ha dado los articulos de %s.", categoria)
        return []
    try:
        datos = respuesta.json()
    except ValueError:
        return []
    miembros = (datos.get("query") or {}).get("categorymembers") or []
    return [m["title"] for m in miembros if m.get("title") and _vale(m["title"])]


def candidatos(cuantos: int = 12, semilla: int | None = None) -> list[str]:
    """Los temas de hoy: primero lo que funciona en YouTube, luego el respaldo.

    El orden importa y es el arreglo de fondo. Antes esto salia de una lista de
    categorias de Wikipedia escrita por mi, o sea de lo que a mi me parecia
    historia interesante - y salio un organismo militar y el reparto de
    indigenas en encomienda. Ahora manda lo que la gente esta viendo.
    """
    azar = random.Random(semilla)
    de_youtube = [t for t, _ in _titulos_que_funcionan()]
    temas = [limpio for limpio in (_tema_de(t) for t in de_youtube) if limpio]
    if temas:
        logger.info("Temas: %s de lo que funciona en YouTube.", len(temas))

    # El respaldo, cuando no hay cuota o la busqueda no da nada. Las categorias
    # siguen aqui por eso, no como fuente principal.
    if len(temas) < cuantos:
        elegidas = azar.sample(CATEGORIAS, min(len(CATEGORIAS), 6))
        for categoria in elegidas:
            articulos = articulos_de(categoria)
            if not articulos:
                continue
            azar.shuffle(articulos)
            temas.extend(articulos[:2])
        logger.info("Temas: completados con categorias hasta %s.", len(temas))

    vistos, salida = set(), []
    for t in temas:
        clave = t.lower()
        if clave not in vistos:
            vistos.add(clave)
            salida.append(t)
    return salida[:cuantos]
