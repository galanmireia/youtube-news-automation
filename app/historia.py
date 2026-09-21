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

from . import research

logger = logging.getLogger(__name__)

# De lo concreto a lo general. Un Short necesita algo que pase, con gente
# dentro: "Batallas de España" da material; "Historia de España" da ensayos.
CATEGORIAS = (
    "Categoría:Batallas de España",
    "Categoría:Asedios",
    "Categoría:Naufragios de España",
    "Categoría:Motines y revueltas en España",
    "Categoría:Atentados en España",
    "Categoría:Epidemias en España",
    "Categoría:Conquista de América",
    "Categoría:Expediciones españolas",
    "Categoría:Reyes de España",
    "Categoría:Monarcas de Castilla",
    "Categoría:Exploradores de España",
    "Categoría:Conquistadores españoles",
    "Categoría:Inquisición española",
    "Categoría:Guerra civil española",
    "Categoría:Reconquista",
    "Categoría:Al-Ándalus",
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
    """Temas posibles para los Shorts de hoy, de categorias distintas.

    De categorias DISTINTAS a proposito: tirando de una sola saldrian cinco
    batallas seguidas, y un canal que repite el mismo tipo de video cinco veces
    aburre antes de que te suscribas.
    """
    azar = random.Random(semilla)
    elegidas = azar.sample(CATEGORIAS, min(len(CATEGORIAS), max(4, cuantos // 2)))
    salida: list[str] = []
    for categoria in elegidas:
        articulos = articulos_de(categoria)
        if not articulos:
            continue
        azar.shuffle(articulos)
        salida.extend(articulos[:2])
    azar.shuffle(salida)
    logger.info("Historia: %s candidatos de %s categorias.", len(salida), len(elegidas))
    return salida[:cuantos]
