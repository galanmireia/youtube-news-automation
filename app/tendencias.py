"""Que se esta viendo HOY, sacado de la lista de tendencias de YouTube.

Hasta ahora el tema salia de los RSS configurados: si una noticia no estaba en
un feed, para el bot no existia. Y el feed no sabe cual de sus titulares le
importa a alguien - eso lo sabe YouTube, que tiene una lista de tendencias por
pais y categoria.

Cuesta UNA unidad de cuota, no cien. La busqueda (search.list) cuesta 100 y
hay 10.000 al dia; la lista de tendencias (videos.list con chart) cuesta 1 y
ademas YA TRAE LAS VISITAS de cada video, o sea que ordenar los temas del dia
por demanda sale gratis en la practica. Por eso esto responde incluso los dias
en que la cuota de busquedas se ha agotado: son metricas distintas.

Lo que esto NO hace, y es deliberado: no convierte un titular de tendencias en
un video. Un titular de otro canal - "Estamos ante algo muy gordo" - no es
material para contar nada; es una señal de que un tema interesa. El material
sigue viniendo de las fuentes de noticias. Lo que aporta esto es el ORDEN: de
lo que ya se puede contar, cual le importa hoy a alguien.
"""
import logging

import requests

from .config import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)

_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"
_TIMEOUT = 25

# 25 es "Noticias y politica". Sin categoria, la lista de tendencias es
# musica y entretenimiento y no dice nada sobre noticias.
CATEGORIA_NOTICIAS = "25"
_MAX = 25


class SinClave(RuntimeError):
    pass


def lo_que_se_ve_hoy(region: str = "ES", categoria: str = CATEGORIA_NOTICIAS) -> list[dict]:
    """Los videos de noticias en tendencia ahora mismo, el mas visto primero."""
    if not YOUTUBE_API_KEY:
        raise SinClave("Falta YOUTUBE_API_KEY; sin ella no se pueden leer las tendencias.")
    params = {
        "part": "snippet,statistics", "chart": "mostPopular",
        "regionCode": region, "videoCategoryId": categoria,
        "maxResults": _MAX, "key": YOUTUBE_API_KEY,
    }
    try:
        r = requests.get(_VIDEOS, params=params, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("No se han podido leer las tendencias: %s", exc)
        return []
    if r.status_code != 200:
        logger.warning("YouTube contesta %s a las tendencias: %s", r.status_code, r.text[:300])
        return []
    try:
        datos = r.json()
    except ValueError:
        return []

    salida = []
    for it in datos.get("items", []):
        sn = it.get("snippet", {})
        try:
            vistas = int(it.get("statistics", {}).get("viewCount", 0))
        except (TypeError, ValueError):
            vistas = 0
        salida.append({
            "titulo": (sn.get("title") or "").strip(),
            "canal": (sn.get("channelTitle") or "").strip(),
            "publicado": (sn.get("publishedAt") or "")[:10],
            "vistas": vistas,
        })
    salida.sort(key=lambda v: v["vistas"], reverse=True)
    logger.info("Tendencias (%s, categoria %s): %s videos, el mas visto con %s visitas.",
                region, categoria, len(salida), salida[0]["vistas"] if salida else 0)
    return salida


def ordenar_por_tendencia(candidatos: list[dict], tendencias: list[dict]) -> list[dict]:
    """Ordena los candidatos segun cuanto se esta viendo hoy su tema.

    Un candidato se empareja con un video en tendencia cuando comparten
    suficientes palabras del titular. No es exacto y no hace falta que lo sea:
    lo unico que decide es el orden, y equivocarse en un emparejamiento
    devuelve el candidato al monton, no lo tira.
    """
    from .news_source import _headline_tokens

    for c in candidatos:
        fichas = _headline_tokens(c.get("title", ""))
        mejor, parecido = 0, ""
        for t in tendencias:
            comunes = fichas & _headline_tokens(t["titulo"])
            # Dos palabras de contenido en comun ya es mucho entre titulares
            # cortos; una sola empareja cualquier cosa con cualquier cosa.
            if len(comunes) >= 2 and t["vistas"] > mejor:
                mejor, parecido = t["vistas"], t["titulo"]
        c["vistas_tendencia"] = mejor
        if mejor:
            logger.info("«%s» esta en tendencias (%s visitas): «%s»",
                        c.get("title", "")[:60], f"{mejor:,}".replace(",", "."), parecido[:60])

    candidatos.sort(key=lambda c: c.get("vistas_tendencia", 0), reverse=True)
    return candidatos


def sin_cubrir(candidatos: list[dict], tendencias: list[dict], cuantos: int = 5) -> list[dict]:
    """Lo que esta en tendencias y NO tiene ninguna noticia detras en los feeds.

    Es el dato que dice si el cuello de botella son las fuentes. Si lo mas
    visto del dia no aparece nunca en los RSS, el problema no es como se
    elige: es que no llega."""
    from .news_source import _headline_tokens
    fichas_cand = [_headline_tokens(c.get("title", "")) for c in candidatos]
    huerfanos = []
    for t in tendencias:
        fichas = _headline_tokens(t["titulo"])
        if not any(len(fichas & f) >= 2 for f in fichas_cand):
            huerfanos.append(t)
    return huerfanos[:cuantos]
