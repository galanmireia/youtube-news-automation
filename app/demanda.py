"""Cuanta gente esta buscando esto AHORA, medido en vez de opinado.

El canal llevaba sesenta y ocho videos eligiendo tema por criterio editorial:
que hubiera personas, que hubiera algo en juego, que se contara bien. Todo eso
importa, pero solo despues de que alguien quiera ver el tema. Y eso no se sabe
mirando la noticia: se sabe mirando YouTube.

La medicion que lo justifica, hecha sobre los videos que ella ya habia
publicado y sus visitas reales:

    consulta                        vistas 7d    sus visitas
    claudia tacoronte               4.953.299    479
    mv doña paz naufragio               7.632      2
    costa concordia capitan             6.043     31
    ms estonia naufragio                2.313     17
    prestige naufragio                    258      9
    sociedades anonimas españa              3      3

Tres ordenes de magnitud entre el que funciono y los que no, y el orden
coincide con lo que paso de verdad. El tema que reventó tenia cinco millones
de visitas repartiendose esa semana; los demas tenian doscientas.

Lo que se mide no es "interes" en abstracto sino DEMANDA YA DEMOSTRADA:
vistas que ya han ocurrido, sobre videos publicados en los ultimos dias. Si
veinticinco videos de esta semana suman cinco millones de visitas, hay gente
buscando eso hoy. Si suman doscientas, no la hay - por buena que sea la
historia.
"""
import logging
import statistics
from datetime import datetime, timedelta, timezone

import requests

from .config import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)

_BUSCAR = "https://www.googleapis.com/youtube/v3/search"
_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"

# Una semana: suficiente para que una noticia de ayer tenga videos y vistas, y
# corto como para que no cuente el interes del mes pasado.
_DIAS = 7
_MAX_RESULTADOS = 25
_TIMEOUT = 25

# search.list cuesta 100 unidades de cuota y videos.list cuesta 1, o sea unas
# 101 por tema. Con las 10.000 diarias caben casi cien temas al dia, que es
# mucho mas de lo que hace falta.
_COSTE_CUOTA = 101


class SinClave(RuntimeError):
    pass


def _get(url: str, params: dict) -> dict:
    if not YOUTUBE_API_KEY:
        raise SinClave(
            "Falta YOUTUBE_API_KEY. Sin ella no se puede medir la demanda, y sin "
            "medirla se elige tema a ciegas, que es lo que veniamos haciendo."
        )
    params = {**params, "key": YOUTUBE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("YouTube no responde midiendo la demanda: %s", exc)
        return {}
    if r.status_code != 200:
        logger.warning("YouTube contesta %s midiendo la demanda: %s",
                       r.status_code, r.text[:300])
        return {}
    try:
        return r.json()
    except ValueError:
        return {}


def medir(consulta: str, dias: int = _DIAS) -> dict:
    """Devuelve la demanda de un tema, o ceros cuando no se ha podido medir.

    La diferencia entre "no hay demanda" y "no he podido medir" importa, asi
    que va marcada: dar por bueno un cero de una peticion fallida descartaria
    un tema que si la tiene."""
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
    datos = _get(_BUSCAR, {
        "part": "snippet", "q": consulta, "type": "video",
        "maxResults": _MAX_RESULTADOS, "order": "viewCount", "publishedAfter": desde,
    })
    if not datos:
        return {"consulta": consulta, "medido": False, "videos": 0,
                "vistas": 0, "mediana": 0, "mejor": 0}

    ids = [i["id"]["videoId"] for i in datos.get("items", []) if i.get("id", {}).get("videoId")]
    if not ids:
        # Medido de verdad, y el resultado es que nadie ha publicado nada.
        return {"consulta": consulta, "medido": True, "videos": 0,
                "vistas": 0, "mediana": 0, "mejor": 0}

    stats = _get(_VIDEOS, {"part": "statistics", "id": ",".join(ids)})
    vistas = [int(v.get("statistics", {}).get("viewCount", 0)) for v in stats.get("items", [])]
    if not vistas:
        return {"consulta": consulta, "medido": False, "videos": len(ids),
                "vistas": 0, "mediana": 0, "mejor": 0}

    return {
        "consulta": consulta,
        "medido": True,
        "videos": len(vistas),
        "vistas": sum(vistas),
        # La mediana y no la media: un solo video viral de un canal enorme
        # dispara la media sin que haya demanda repartida.
        "mediana": int(statistics.median(vistas)),
        "mejor": max(vistas),
    }


def resumen(m: dict) -> str:
    if not m.get("medido"):
        return f"«{m['consulta']}»: no se ha podido medir."
    if not m["videos"]:
        return f"«{m['consulta']}»: nadie ha publicado nada esta semana. Sin demanda."
    return (f"«{m['consulta']}»: {m['vistas']:,} vistas en 7 dias, "
            f"{m['videos']} videos, mediana {m['mediana']:,}").replace(",", ".")
