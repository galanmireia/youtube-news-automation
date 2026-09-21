"""Que canales estan funcionando y cuales podriamos replicar.

Idea suya, y es la que faltaba: llevamos meses mejorando COMO se hace el video
y cero tiempo mirando QUE funciona ya. El canal elige tema por criterio -
ahora por calendario de efemerides - y luego se sorprende de las visitas. Lo
que propone es al reves: mirar quien lo esta petando con un formato que
nosotros podemos copiar, y meternos ahi.

LO QUE ESTO NO HACE, Y CONVIENE DECIRLO: no detecta si un video esta hecho con
IA. No hay forma fiable de saberlo desde la API, y fingir que si la hay seria
peor que no mirarlo. Lo que se puede medir es otra cosa, y resulta que es la
que de verdad importa:

  - CANAL JOVEN. Si un canal de ocho meses tiene cien mil suscriptores, lo que
    sea que hace funciona HOY, no en 2019 con otro algoritmo.
  - MUCHOS VIDEOS PARA SU EDAD. Un canal que sube cada dos dias no esta
    grabando en plato: monta. Y montar es lo que hace esta arquitectura.
  - VISTAS POR VIDEO ALTAS. Que el canal sea grande no basta: si tiene dos mil
    videos y un millon de visitas, cada video da quinientas.

Un canal que cumple los tres es replicable, sea quien sea quien lo hace. Y esa
es la pregunta util, no si es una IA.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from .config import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)

_BUSCAR = "https://www.googleapis.com/youtube/v3/search"
_CANALES = "https://www.googleapis.com/youtube/v3/channels"

# search.list cuesta CIEN unidades; channels.list cuesta UNA. De ahi la forma
# de esto: pocas busquedas y muchas consultas baratas encima. Con tres semillas
# son 300 unidades de las 10.000 del dia.
_COSTE_BUSQUEDA = 100
_MAX_POR_BUSQUEDA = 50

# Un canal de mas de dos años ya no dice que funciona hoy: dice que funcionaba.
_MESES_MAXIMO = 26
# El umbral de monetizacion de YouTube es mil suscriptores. Por debajo no
# sabemos si le da dinero a nadie; por encima, al menos es posible.
_SUSCRIPTORES_MINIMO = 1000
# Y un techo, porque un canal de diez millones no es replicable: tiene equipo.
_SUSCRIPTORES_MAXIMO = 3_000_000


class SinClave(RuntimeError):
    pass


class SinCuota(RuntimeError):
    pass


def _pedir(url: str, params: dict) -> dict:
    if not YOUTUBE_API_KEY:
        raise SinClave("No hay YOUTUBE_API_KEY configurada.")
    r = requests.get(url, params={**params, "key": YOUTUBE_API_KEY}, timeout=30)
    if r.status_code == 403 and "quota" in r.text.lower():
        raise SinCuota("Se ha agotado la cuota de YouTube por hoy. Se reinicia a las 09:00.")
    r.raise_for_status()
    return r.json()


def _canales_de(consulta: str, dias: int, region: str, idioma: str) -> dict[str, str]:
    """Los canales detras de los videos mas vistos de este tema. Cien unidades."""
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat().replace("+00:00", "Z")
    datos = _pedir(_BUSCAR, {
        "part": "snippet", "q": consulta, "type": "video",
        "order": "viewCount", "publishedAfter": desde,
        "regionCode": region, "relevanceLanguage": idioma,
        "maxResults": _MAX_POR_BUSQUEDA,
    })
    salida = {}
    for item in datos.get("items", []):
        canal = item.get("snippet", {}).get("channelId")
        if canal:
            salida.setdefault(canal, item["snippet"].get("title", ""))
    return salida


def _ficha(ids: list[str]) -> list[dict]:
    """Los datos de hasta cincuenta canales por UNA unidad de cuota."""
    fichas = []
    for i in range(0, len(ids), 50):
        datos = _pedir(_CANALES, {
            "part": "snippet,statistics", "id": ",".join(ids[i:i + 50]),
        })
        fichas.extend(datos.get("items", []))
    return fichas


def _medir(ficha: dict) -> dict | None:
    est = ficha.get("statistics", {})
    if est.get("hiddenSubscriberCount"):
        return None
    try:
        subs = int(est.get("subscriberCount", 0))
        videos = int(est.get("videoCount", 0))
        vistas = int(est.get("viewCount", 0))
    except (TypeError, ValueError):
        return None
    if not videos:
        return None

    creado = ficha.get("snippet", {}).get("publishedAt", "")
    try:
        nacido = datetime.fromisoformat(creado.replace("Z", "+00:00"))
    except ValueError:
        return None
    meses = max(1.0, (datetime.now(timezone.utc) - nacido).days / 30.4)

    return {
        "id": ficha.get("id", ""),
        "nombre": ficha.get("snippet", {}).get("title", ""),
        "meses": round(meses, 1),
        "subs": subs,
        "videos": videos,
        "vistas": vistas,
        "por_video": int(vistas / videos),
        # Videos al mes. Por encima de ocho no hay nadie grabando en plato.
        "ritmo": round(videos / meses, 1),
        # Suscriptores ganados al mes: lo que de verdad dice si va hacia arriba.
        "subs_mes": int(subs / meses),
    }


def replicable(c: dict) -> tuple[bool, str]:
    """¿Podriamos nosotros hacer algo asi? Con el motivo, que es lo que se lee."""
    if c["meses"] > _MESES_MAXIMO:
        return False, f"demasiado veterano ({c['meses']:.0f} meses)"
    if c["subs"] < _SUSCRIPTORES_MINIMO:
        return False, "por debajo del umbral de monetizacion"
    if c["subs"] > _SUSCRIPTORES_MAXIMO:
        return False, "demasiado grande, eso ya es un equipo"
    if c["ritmo"] < 4:
        return False, f"sube poco ({c['ritmo']}/mes), no es un formato de montaje"
    if c["por_video"] < 3000:
        return False, f"solo {c['por_video']:,} vistas por video".replace(",", ".")
    return True, "joven, sube mucho y le ven"


def explorar(semillas: list[str], dias: int = 90,
             region: str = "ES", idioma: str = "es") -> tuple[list[dict], int]:
    """Los canales replicables que aparecen buscando estas semillas.

    Devuelve (canales ordenados, cuota gastada)."""
    encontrados: dict[str, str] = {}
    gastado = 0
    for semilla in semillas:
        encontrados.update(_canales_de(semilla, dias, region, idioma))
        gastado += _COSTE_BUSQUEDA

    if not encontrados:
        return [], gastado

    fichas = _ficha(list(encontrados))
    gastado += max(1, len(encontrados) // 50 + 1)

    medidos = [m for m in (_medir(f) for f in fichas) if m]
    buenos = []
    for c in medidos:
        vale, motivo = replicable(c)
        c["motivo"] = motivo
        if vale:
            buenos.append(c)

    # Por suscriptores ganados al mes: es lo que separa "grande" de "creciendo".
    buenos.sort(key=lambda c: -c["subs_mes"])
    logger.info("Nichos: %s canales vistos, %s replicables (cuota %s).",
                len(medidos), len(buenos), gastado)
    return buenos, gastado
